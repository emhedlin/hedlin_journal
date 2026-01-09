#!/usr/bin/env python3
"""
Load configuration from config.toml and make it available to templates.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib


@dataclass
class ThemeConfig:
    background: str = "#f5f5f5"
    text: str = "#131313"
    muted: str = "#999999"
    border: str = "#e0e0e0"
    hover: str = "#000000"


@dataclass
class PreviewConfig:
    word_count: int = 8


@dataclass
class SiteConfig:
    title: str = "A Hedlin Family Journal"
    subtitle: str = ""


@dataclass
class Config:
    theme: ThemeConfig
    preview: PreviewConfig
    site: SiteConfig

    def to_css_vars(self) -> str:
        """Generate CSS custom properties from theme config."""
        return f"""
--color-bg: {self.theme.background};
--color-text: {self.theme.text};
--color-muted: {self.theme.muted};
--color-border: {self.theme.border};
--color-hover: {self.theme.hover};
""".strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for template rendering."""
        return {
            'theme': self.theme.__dict__,
            'preview': self.preview.__dict__,
            'site': self.site.__dict__,
        }


def load_config(config_path: Path = None) -> Config:
    """Load configuration from config.toml."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.toml"

    if not config_path.exists():
        return Config(
            theme=ThemeConfig(),
            preview=PreviewConfig(),
            site=SiteConfig()
        )

    with open(config_path, 'rb') as f:
        data = tomllib.load(f)

    theme_data = data.get('theme', {})
    preview_data = data.get('preview', {})
    site_data = data.get('site', {})

    return Config(
        theme=ThemeConfig(**theme_data),
        preview=PreviewConfig(**preview_data),
        site=SiteConfig(**site_data)
    )


# For CLI usage
if __name__ == "__main__":
    config = load_config()
    print("Configuration loaded:")
    print(f"  Theme: {config.theme}")
    print(f"  Preview: {config.preview}")
    print(f"  Site: {config.site}")
