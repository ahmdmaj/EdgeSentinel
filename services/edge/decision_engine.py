def evaluate_routing_policy(severity: str, network_latency_ms: float, edge_cpu_percent: float) -> str:
    """
    Determines whether a telemetry payload should be processed at the EDGE, CLOUD, or HYBRID
    based on simulated system conditions.
    """
    if edge_cpu_percent > 80:
        return "CLOUD"
    
    if severity == "CRITICAL" or network_latency_ms > 200:
        return "EDGE"
        
    return "HYBRID"
