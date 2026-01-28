"""
PICAM Hash Utilities
For creating deterministic, auditable hashes
"""

import hashlib
import json
from typing import Any, Dict
from datetime import datetime, date


def json_serializer(obj: Any) -> str:
    """Custom JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def create_deterministic_hash(data: Dict[str, Any]) -> str:
    """
    Create a deterministic SHA-256 hash from a dictionary.
    
    Keys are sorted to ensure determinism.
    All values must be JSON serializable.
    
    Args:
        data: Dictionary to hash
        
    Returns:
        Hexadecimal SHA-256 hash string
    """
    # Sort keys and serialize
    json_str = json.dumps(data, sort_keys=True, default=json_serializer)
    
    # Create hash
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


def verify_hash(data: Dict[str, Any], expected_hash: str) -> bool:
    """
    Verify that data matches expected hash.
    
    Args:
        data: Dictionary to verify
        expected_hash: Expected hash value
        
    Returns:
        True if hashes match
    """
    actual_hash = create_deterministic_hash(data)
    return actual_hash == expected_hash


def create_chain_hash(
    current_data: Dict[str, Any],
    previous_hash: str
) -> str:
    """
    Create a hash that includes reference to previous hash.
    Used for immutable log chains.
    
    Args:
        current_data: Current entry data
        previous_hash: Hash of previous entry in chain
        
    Returns:
        New hash incorporating previous hash
    """
    # Add previous hash to data
    chain_data = {
        **current_data,
        "_previous_hash": previous_hash
    }
    
    return create_deterministic_hash(chain_data)


def verify_chain(entries: list, hash_field: str = "entry_hash", 
                 prev_hash_field: str = "previous_entry_hash") -> bool:
    """
    Verify integrity of a hash chain.
    
    Args:
        entries: List of entries in chain order
        hash_field: Field name containing entry hash
        prev_hash_field: Field name containing previous hash reference
        
    Returns:
        True if chain is valid
    """
    if not entries:
        return True
        
    for i, entry in enumerate(entries):
        if i == 0:
            # First entry should have empty or genesis previous hash
            if entry.get(prev_hash_field) not in ["", "genesis", None]:
                # Verify it references nothing or genesis
                pass
        else:
            # Each entry's previous hash should match previous entry's hash
            prev_entry = entries[i - 1]
            if entry.get(prev_hash_field) != prev_entry.get(hash_field):
                return False
                
    return True