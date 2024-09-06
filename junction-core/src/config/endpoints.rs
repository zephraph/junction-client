use serde::Deserialize;
use std::{net::SocketAddr, time::Duration};
use xds_api::pb::envoy::config::{
    core::v3 as xds_core, endpoint::v3 as xds_endpoint, route::v3 as xds_route,
};

// FIXME: do we need to to support returning filters/rewrites? does supporting
//        header filters mean adding headers to Endpoint?

/// An HTTP endpoint to make a request to.
///
/// Endpoints contain both a target [url][crate::Url] that should be given to an
/// HTTP client and an [address][EndpointAddress] that indicates the address the
/// the hostname in the URL should resolve to. See [EndpointAddress] for more
/// information on how and when to resolve an address.
#[derive(Debug)]
pub struct Endpoint {
    pub url: crate::Url,
    pub timeout: Duration,
    pub retry: Option<RetryPolicy>,
    pub address: EndpointAddress,
}

/// The address of an endpoint.
///
/// Depending on the type of endpoint, addresses may need to be further resolved by
/// a client implementation.
#[derive(Clone, Debug, Hash)]
pub enum EndpointAddress {
    /// A resolved IP address and port. This address can be used for a request
    /// without any further resolution.
    SocketAddr(SocketAddr),

    /// A DNS name and port. The name should be resolved periodically by the HTTP
    /// client and used to direct traffic.
    ///
    /// This name may be different than the hostname part of an [Endpoint]'s `url`.
    DnsName(String, u32),
}

impl std::fmt::Display for EndpointAddress {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            EndpointAddress::SocketAddr(addr) => addr.fmt(f),
            EndpointAddress::DnsName(name, port) => write!(f, "{name}:{port}"),
        }
    }
}

impl EndpointAddress {
    pub(crate) fn from_socket_addr(xds_address: &xds_core::SocketAddress) -> Option<Self> {
        let ip = xds_address.address.parse().ok()?;
        let port: u16 = match xds_address.port_specifier.as_ref()? {
            xds_core::socket_address::PortSpecifier::PortValue(port) => (*port).try_into().ok()?,
            _ => return None,
        };

        Some(Self::SocketAddr(SocketAddr::new(ip, port)))
    }

    #[allow(unused)]
    pub(crate) fn from_dns_name(xds_address: &xds_core::SocketAddress) -> Option<Self> {
        let address = xds_address.address.clone();
        let port = match xds_address.port_specifier.as_ref()? {
            xds_core::socket_address::PortSpecifier::PortValue(port) => port,
            _ => return None,
        };

        Some(Self::DnsName(address, *port))
    }

    pub(crate) fn from_xds_lb_endpoint<F>(endpoint: &xds_endpoint::LbEndpoint, f: F) -> Option<Self>
    where
        F: Fn(&xds_core::SocketAddress) -> Option<EndpointAddress>,
    {
        let endpoint = match endpoint.host_identifier.as_ref()? {
            xds_endpoint::lb_endpoint::HostIdentifier::Endpoint(ep) => ep,
            xds_endpoint::lb_endpoint::HostIdentifier::EndpointName(_) => return None,
        };

        let address = endpoint.address.as_ref().and_then(|a| a.address.as_ref())?;
        match address {
            xds_core::address::Address::SocketAddress(socket_address) => f(socket_address),
            _ => None,
        }
    }
}

// TODO: add a way to configure the methods/statuses retries are allowed on.
// right now this just uses the default client lib behavior.
//
// NOTE: this differs slightly from the GRPC retry policy mapping to/from xDS: https://github.com/grpc/proposal/blob/master/A44-xds-retry.md#converting-envoy-retrypolicy-to-grpc-retrypolicy
#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct RetryPolicy {
    pub max_attempts: usize,
    pub initial_backoff: Duration,
    pub max_backoff: Duration,
}

impl RetryPolicy {
    pub(crate) fn from_xds(r: &xds_route::RetryPolicy) -> Self {
        let (initial, max) = r
            .retry_back_off
            .as_ref()
            .map(|r| (r.base_interval.clone(), r.max_interval.clone()))
            .unwrap_or((None, None));

        let max_attempts = r.num_retries.clone().map_or(1, |v| v.into()) as usize;
        let initial_backoff = initial
            .and_then(|v| v.try_into().ok())
            .unwrap_or(Duration::from_millis(5));
        let max_backoff = max
            .and_then(|v| v.try_into().ok())
            .unwrap_or(Duration::from_secs(2));

        Self {
            max_attempts,
            initial_backoff,
            max_backoff,
        }
    }
}
