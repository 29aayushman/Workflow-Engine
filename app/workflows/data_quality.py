"""
Data Quality Pipeline Workflow (Option C).
Demonstrates profile → identify anomalies → generate rules → apply rules → loop until quality threshold met.
"""
from typing import Dict, Any
import logging
from app.engine.registry import tool_registry
from app.engine.models import Graph, Node, Edge

logger = logging.getLogger(__name__)


# ========== Tool Functions ==========

def profile_data(state: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Profile the data to generate basic statistics.
    
    Args:
        state: Must contain 'data' key with list of records
        params: Optional parameters for profiling
        
    Returns:
        Dictionary with profile statistics
    """
    data = state.get("data", [])
    
    if not data:
        logger.warning("No data found for profiling")
        return {
            "profile": {
                "total_records": 0,
                "fields": [],
                "null_counts": {}
            }
        }
    
    # Basic profiling
    total_records = len(data)
    
    # Get field names from first record
    if isinstance(data[0], dict):
        fields = list(data[0].keys())
        
        # Count nulls/missing values per field
        null_counts = {}
        numeric_stats = {}
        
        for field in fields:
            null_count = sum(1 for record in data if record.get(field) is None or record.get(field) == "")
            null_counts[field] = null_count
            
            # Basic numeric stats
            numeric_values = [record.get(field) for record in data 
                            if isinstance(record.get(field), (int, float))]
            
            if numeric_values:
                numeric_stats[field] = {
                    "min": min(numeric_values),
                    "max": max(numeric_values),
                    "avg": sum(numeric_values) / len(numeric_values),
                    "count": len(numeric_values)
                }
    else:
        fields = []
        null_counts = {}
        numeric_stats = {}
    
    profile = {
        "total_records": total_records,
        "fields": fields,
        "null_counts": null_counts,
        "numeric_stats": numeric_stats
    }
    
    logger.info(f"Profiled {total_records} records with {len(fields)} fields")
    
    return {"profile": profile}


def identify_anomalies(state: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identify anomalies in the data based on profiling results.
    
    Args:
        state: Must contain 'data' and 'profile'
        params: Can contain 'null_threshold' (default 0.1 = 10%)
        
    Returns:
        Dictionary with anomaly_count and anomalies list
    """
    data = state.get("data", [])
    profile = state.get("profile", {})
    null_threshold = params.get("null_threshold", 0.1)
    
    anomalies = []
    total_records = profile.get("total_records", len(data))
    
    if total_records == 0:
        return {"anomaly_count": 0, "anomalies": []}
    
    # Check for high null rates
    null_counts = profile.get("null_counts", {})
    for field, null_count in null_counts.items():
        null_rate = null_count / total_records
        if null_rate > null_threshold:
            anomalies.append({
                "type": "high_null_rate",
                "field": field,
                "null_count": null_count,
                "null_rate": null_rate,
                "threshold": null_threshold
            })
    
    # Check for outliers in numeric fields
    numeric_stats = profile.get("numeric_stats", {})
    for field, stats in numeric_stats.items():
        if stats["count"] == 0:
            continue
            
        avg = stats["avg"]
        min_val = stats["min"]
        max_val = stats["max"]
        
        range_size = max_val - min_val
        if range_size > 0:
            outlier_threshold = avg + (range_size * 2)
            
            for record in data:
                value = record.get(field)
                if isinstance(value, (int, float)) and value > outlier_threshold:
                    anomalies.append({
                        "type": "outlier",
                        "field": field,
                        "value": value,
                        "threshold": outlier_threshold
                    })
    
    # Check for duplicate records
    if data and isinstance(data[0], dict):
        seen = set()
        for idx, record in enumerate(data):
            record_tuple = tuple(sorted(record.items()))
            if record_tuple in seen:
                anomalies.append({
                    "type": "duplicate",
                    "record_index": idx
                })
            seen.add(record_tuple)
    
    logger.info(f"Identified {len(anomalies)} anomalies")
    
    return {
        "anomaly_count": len(anomalies),
        "anomalies": anomalies
    }


def generate_rules(state: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate data quality rules based on identified anomalies.
    
    Args:
        state: Must contain 'anomalies' and 'profile'
        params: Optional rule generation parameters
        
    Returns:
        Dictionary with generated rules
    """
    anomalies = state.get("anomalies", [])
    profile = state.get("profile", {})
    
    rules = []
    
    for anomaly in anomalies:
        if anomaly["type"] == "high_null_rate":
            rules.append({
                "rule_type": "not_null",
                "field": anomaly["field"],
                "description": f"Field '{anomaly['field']}' should not be null",
                "action": "flag_or_fill"
            })
        
        elif anomaly["type"] == "outlier":
            rules.append({
                "rule_type": "range_check",
                "field": anomaly["field"],
                "max_value": anomaly["threshold"],
                "description": f"Field '{anomaly['field']}' should be <= {anomaly['threshold']}",
                "action": "cap_or_remove"
            })
        
        elif anomaly["type"] == "duplicate":
            rules.append({
                "rule_type": "unique",
                "description": "Remove duplicate records",
                "action": "remove_duplicates"
            })
    
    fields = profile.get("fields", [])
    numeric_stats = profile.get("numeric_stats", {})
    
    for field in fields:
        if field in numeric_stats:
            rules.append({
                "rule_type": "type_check",
                "field": field,
                "expected_type": "numeric",
                "description": f"Field '{field}' should be numeric",
                "action": "validate_or_convert"
            })
    
    logger.info(f"Generated {len(rules)} quality rules")
    
    return {"rules": rules}


def apply_rules(state: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply data quality rules to clean the data.
    
    Args:
        state: Must contain 'data', 'rules'
        params: Optional application parameters
        
    Returns:
        Dictionary with cleaned data and updated anomaly_count
    """
    data = state.get("data", [])
    rules = state.get("rules", [])
    
    if not data:
        return {"data": [], "anomaly_count": 0, "rules_applied": 0}
    
    cleaned_data = data.copy()
    rules_applied = 0
    
    for rule in rules:
        rule_type = rule.get("rule_type")
        
        if rule_type == "not_null":
            field = rule["field"]
            for record in cleaned_data:
                if isinstance(record, dict):
                    if record.get(field) is None or record.get(field) == "":
                        record[field] = 0
            rules_applied += 1
        
        elif rule_type == "range_check":
            field = rule["field"]
            max_value = rule.get("max_value")
            for record in cleaned_data:
                if isinstance(record, dict):
                    value = record.get(field)
                    if isinstance(value, (int, float)) and value > max_value:
                        record[field] = max_value
            rules_applied += 1
        
        elif rule_type == "unique":
            seen = set()
            unique_data = []
            for record in cleaned_data:
                if isinstance(record, dict):
                    record_tuple = tuple(sorted(record.items()))
                    if record_tuple not in seen:
                        unique_data.append(record)
                        seen.add(record_tuple)
            cleaned_data = unique_data
            rules_applied += 1
    
    remaining_anomalies = 0
    for record in cleaned_data:
        if isinstance(record, dict):
            for value in record.values():
                if value is None or value == "":
                    remaining_anomalies += 1
    
    logger.info(f"Applied {rules_applied} rules, {remaining_anomalies} anomalies remaining")
    
    return {
        "data": cleaned_data,
        "anomaly_count": remaining_anomalies,
        "rules_applied": rules_applied
    }


# ========== Register Tools ==========

def register_data_quality_tools():
    """Register all data quality workflow tools."""
    tool_registry.register("profile_data", profile_data)
    tool_registry.register("identify_anomalies", identify_anomalies)
    tool_registry.register("generate_rules", generate_rules)
    tool_registry.register("apply_rules", apply_rules)
    logger.info("Registered data quality workflow tools")


# Auto-register tools when module is imported
register_data_quality_tools()
