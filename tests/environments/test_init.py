import pytest

from minisweagent.environments import get_environment_class
from minisweagent.environments.local import LocalEnvironment
from minisweagent.environments.exploit_environment_v2 import ExploitFoundryEnvironmentV2
from minisweagent.environments.exploit_environment_v3 import ExploitFoundryEnvironmentV3


class TestGetEnvironmentClass:
    def test_get_environment_class_local_full_path(self):
        """Test that get_environment_class returns LocalEnvironment when given full module path."""
        env_class = get_environment_class("minisweagent.environments.local.LocalEnvironment")
        assert env_class is LocalEnvironment

    def test_get_environment_class_local_shorthand(self):
        """Test that get_environment_class returns LocalEnvironment when given shorthand."""
        env_class = get_environment_class("local")
        assert env_class is LocalEnvironment

    def test_get_environment_class_exploit_foundry_v2_shorthand(self):
        """Test that get_environment_class returns ExploitFoundryEnvironmentV2 for v2 shorthand."""
        env_class = get_environment_class("exploit_foundry_v2")
        assert env_class is ExploitFoundryEnvironmentV2

    def test_get_environment_class_exploit_foundry_v3_shorthand(self):
        """Test that get_environment_class returns ExploitFoundryEnvironmentV3 for v3 shorthand."""
        env_class = get_environment_class("exploit_foundry_v3")
        assert env_class is ExploitFoundryEnvironmentV3

    def test_get_environment_class_invalid_spec(self):
        """Test that get_environment_class raises ValueError for invalid spec."""
        with pytest.raises(ValueError, match="Unknown environment type"):
            get_environment_class("invalid_environment")

    def test_get_environment_class_invalid_module(self):
        """Test that get_environment_class raises ValueError for non-existent module."""
        with pytest.raises(ValueError, match="Unknown environment type"):
            get_environment_class("nonexistent.module.Class")
