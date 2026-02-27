"""Execution parameters for mfoc-hardnested."""

from dataclasses import dataclass
from typing import List


@dataclass
class ExecutionParams:
  """User-provided CLI-equivalent parameters."""

  output_file: str = ""
  probes_per_sector: int = 20
  nonce_tolerance: int = 20
  extra_key_hex: str = ""
  keys_file: str = ""
  skip_default_keys: bool = False
  force_hardnested: bool = False
  reduce_memory: bool = False

  def to_args(self) -> List[str]:
    """Build argument list matching mfoc-hardnested options."""
    args: List[str] = []
    if self.skip_default_keys:
      args.append("-C")
    if self.force_hardnested:
      args.append("-F")
    if self.reduce_memory:
      args.append("-Z")
    if self.extra_key_hex:
      args.extend(["-k", self.extra_key_hex])
    if self.keys_file:
      args.extend(["-f", self.keys_file])
    args.extend(["-P", str(self.probes_per_sector)])
    args.extend(["-T", str(self.nonce_tolerance)])
    if self.output_file:
      args.extend(["-O", self.output_file])
    return args
