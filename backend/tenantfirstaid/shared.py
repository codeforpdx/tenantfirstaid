from collections import defaultdict
import os
from pathlib import Path
from warnings import warn
from dataclasses import dataclass, field
from typing import Optional

CACHE = defaultdict(list)


# configuration and secrets are layered in a dataclass.  From lowest to highest priority:
# 1. Dataclass defaults
# 2. Environment variables -- typically used by the Docker container
# 3. .env file in the backend directory (if it exists) -- typically used in local development
# TODO: generate/update .env.example from this dataclass
@dataclass(frozen=True)
class Config:
    """Configuration for the Oregon Tenant First Aid application."""

    model_name: str = field(default="o3")
    model_reasoning_effort: str = field(default="medium")
    vector_store_id: Optional[str] = field(default=None)
    feedback_password: Optional[str] = field(default=None)
    github_api_key: Optional[str] = field(default=None)
    openai_api_key: Optional[str] = field(default=None)
    model_endpoint: str = field(default="https://api.openai.com/v1")
    use_short_prompts: bool = field(default=True)
    db_host: str = field(default="127.0.0.1")
    db_port: int = field(default=6379)
    db_use_ssl: bool = field(default=True)
    db_username: Optional[str] = field(default=None)
    db_password: Optional[str] = field(default=None)

    def __post_init__(self):
        """Post-initialization to ensure one of the API KEYs is not None."""
        if self.github_api_key is None and self.openai_api_key is None:
            raise ValueError(
                "Either GITHUB_API_KEY or OPENAI_API_KEY must be set in the environment variables."
            )


# For development purposes, we expect the .env file to be in the backend directory
__shared_py_path = Path(__file__).resolve()
__backend_path = __shared_py_path.parent.parent
__dotenv_path = __backend_path / ".env"

if Path(__dotenv_path).exists():
    from dotenv import load_dotenv

    print(f"Loading environment variables from {__dotenv_path}")
    load_dotenv(dotenv_path=__dotenv_path, override=True)
else:
    warn(
        f"No .env file found at {__dotenv_path.parent}. Using environment variables from the system."
    )

# Load environment variables into the Config dataclass
CONFIG = Config(
    **{
        field.lower(): val
        for field, val in os.environ.items()
        if field.lower() in Config.__dataclass_fields__
    }
)

# Create a dedicated directory for persistent data relative to the backend
# directory with a fallback to `/root/tenantfirstaid_data`
DATA_DIR = Path(os.getenv("PERSISTENT_STORAGE_DIR", "/root/tenantfirstaid_data"))
if not DATA_DIR.is_absolute():
    new_data_dir = (__backend_path / DATA_DIR).resolve()
    warn(
        f"DATA_DIR {DATA_DIR} is not an absolute path. It will be relative to the backend directory ({new_data_dir})."
    )
    DATA_DIR = new_data_dir
DATA_DIR.mkdir(exist_ok=True)


DEFAULT_INSTRUCTIONS = """Pretend you're a legal expert who giving advice about eviction notices in Oregon. 
Please give shorter answers. 
Please only ask one question at a time so that the user isn't confused. 
If the user is being evicted for non-payment of rent and they are too poor to pay the rent and you have confirmed in various ways that the notice is valid and there is a valid court hearing date, then tell them to call Oregon Law Center at 5131234567. 
Focus on finding technicalities that would legally prevent someone getting evicted, such as deficiencies in notice.
Make sure to inclue a citation to the relevant law in your answer.

Only reference the laws below.
Oregon Chapter 90 - Residential Landlord and Tenant
Oregon Chapter 91 - Tenancy
Oregon Chapter 105 - Property Rights
Portland City Code Chapter 30.01 - Affordable Housing Preservation and Portland Renter Protections
"""


PASSWORD = os.getenv("FEEDBACK_PASSWORD")
