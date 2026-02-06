"""
WinGamingDiag - Custom Rule Engine
Allows users to define custom diagnostic rules
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
import json
import yaml


@dataclass
class CustomRule:
    """A custom diagnostic rule defined by user"""
    id: str
    name: str
    description: str
    category: str
    severity: str
    condition: str
    threshold: Any
    recommendation: str
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'severity': self.severity,
            'condition': self.condition,
            'threshold': self.threshold,
            'recommendation': self.recommendation,
            'enabled': self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CustomRule':
        """Create from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            category=data.get('category', 'custom'),
            severity=data.get('severity', 'low'),
            condition=data['condition'],
            threshold=data['threshold'],
            recommendation=data.get('recommendation', ''),
            enabled=data.get('enabled', True)
        )


class CustomRuleEngine:
    """
    Engine for loading and evaluating custom diagnostic rules.
    Supports JSON and YAML rule definitions.
    """
    
    # Built-in example rules
    EXAMPLE_RULES = [
        CustomRule(
            id="custom_high_memory_custom",
            name="High Memory Usage Threshold",
            description="Trigger when memory usage exceeds custom threshold",
            category="performance",
            severity="medium",
            condition="memory_usage_percent > threshold",
            threshold=75.0,
            recommendation="Close unused applications to free memory"
        ),
        CustomRule(
            id="custom_low_disk_space_custom",
            name="Low Disk Space Warning",
            description="Trigger when free disk space is below threshold",
            category="performance",
            severity="high",
            condition="disk_free_gb < threshold",
            threshold=50.0,
            recommendation="Free up disk space or move files to external storage"
        ),
        CustomRule(
            id="custom_old_gpu_driver_custom",
            name="GPU Driver Age Check",
            description="Warn if GPU driver is older than threshold days",
            category="hardware",
            severity="medium",
            condition="gpu_driver_age_days > threshold",
            threshold=90,
            recommendation="Update GPU driver for better performance and compatibility"
        ),
        CustomRule(
            id="custom_cpu_temperature_custom",
            name="CPU Temperature Monitor",
            description="Alert when CPU temperature is too high",
            category="hardware",
            severity="high",
            condition="cpu_temperature_celsius > threshold",
            threshold=80.0,
            recommendation="Check CPU cooling and clean dust from heatsinks"
        )
    ]
    
    def __init__(self, rules_dir: Optional[Path] = None):
        """
        Initialize custom rule engine
        
        Args:
            rules_dir: Directory containing custom rule files
        """
        if rules_dir is None:
            self.rules_dir = Path.home() / "AppData" / "Local" / "WinGamingDiag" / "rules"
        else:
            self.rules_dir = Path(rules_dir)
        
        self.rules_dir.mkdir(parents=True, exist_ok=True)
        self.rules_file = self.rules_dir / "custom_rules.json"
        self.rules: List[CustomRule] = []
        
        # Load existing rules
        self.load_rules()
    
    def load_rules(self) -> None:
        """Load custom rules from file"""
        if not self.rules_file.exists():
            # Create with example rules
            self.rules = self.EXAMPLE_RULES.copy()
            self.save_rules()
            return
        
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                self.rules = [CustomRule.from_dict(r) for r in data]
            else:
                self.rules = []
                
        except Exception:
            self.rules = self.EXAMPLE_RULES.copy()
    
    def save_rules(self) -> bool:
        """Save custom rules to file"""
        try:
            data = [rule.to_dict() for rule in self.rules]
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False
    
    def add_rule(self, rule: CustomRule) -> bool:
        """
        Add a new custom rule
        
        Args:
            rule: CustomRule to add
            
        Returns:
            True if added successfully
        """
        # Check for duplicate ID
        if any(r.id == rule.id for r in self.rules):
            return False
        
        self.rules.append(rule)
        return self.save_rules()
    
    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove a custom rule
        
        Args:
            rule_id: ID of rule to remove
            
        Returns:
            True if removed successfully
        """
        original_count = len(self.rules)
        self.rules = [r for r in self.rules if r.id != rule_id]
        
        if len(self.rules) < original_count:
            return self.save_rules()
        return False
    
    def update_rule(self, rule_id: str, **kwargs) -> bool:
        """
        Update an existing rule
        
        Args:
            rule_id: ID of rule to update
            **kwargs: Fields to update
            
        Returns:
            True if updated successfully
        """
        for rule in self.rules:
            if rule.id == rule_id:
                for key, value in kwargs.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                return self.save_rules()
        return False
    
    def get_enabled_rules(self) -> List[CustomRule]:
        """Get all enabled rules"""
        return [r for r in self.rules if r.enabled]
    
    def import_rules_from_yaml(self, yaml_path: Path) -> int:
        """
        Import rules from YAML file
        
        Args:
            yaml_path: Path to YAML file
            
        Returns:
            Number of rules imported
        """
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, list):
                return 0
            
            imported = 0
            for rule_data in data:
                try:
                    rule = CustomRule.from_dict(rule_data)
                    if self.add_rule(rule):
                        imported += 1
                except Exception:
                    continue
            
            return imported
            
        except Exception:
            return 0
    
    def export_rules_to_yaml(self, yaml_path: Path) -> bool:
        """
        Export rules to YAML file
        
        Args:
            yaml_path: Path to export YAML file
            
        Returns:
            True if successful
        """
        try:
            data = [rule.to_dict() for rule in self.rules]
            with open(yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False)
            return True
        except Exception:
            return False
    
    def validate_rule(self, rule: CustomRule) -> List[str]:
        """
        Validate a custom rule
        
        Args:
            rule: Rule to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not rule.id:
            errors.append("Rule ID is required")
        
        if not rule.name:
            errors.append("Rule name is required")
        
        if not rule.condition:
            errors.append("Rule condition is required")
        
        # Validate condition syntax (basic check)
        valid_conditions = [
            'memory_usage_percent',
            'disk_free_gb',
            'disk_usage_percent',
            'cpu_temperature_celsius',
            'gpu_temperature_celsius',
            'gpu_driver_age_days',
            'uptime_hours'
        ]
        
        if not any(cond in rule.condition for cond in valid_conditions):
            errors.append(f"Condition must contain one of: {', '.join(valid_conditions)}")
        
        return errors


__all__ = ['CustomRuleEngine', 'CustomRule']