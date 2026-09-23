from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

RegionKind = Literal["header", "summary", "main", "secondary", "sidebar", "footer"]


@dataclass(frozen=True)
class RegionSlot:
    band: int
    band_weight: int
    column_order: int
    column_weight: int


@dataclass(frozen=True)
class TemplateSkeleton:
    id: str
    region_columns: Mapping[RegionKind, int]
    region_slots: Mapping[RegionKind, RegionSlot]
    slot_gap: int
    safe_margin_x: int
    safe_margin_y: int
    title_height: int
    theme_tokens: Mapping[str, Mapping[str, str | int]]


_DARK_TOKENS = MappingProxyType(
    {
        "font_family": "Inter, system-ui, sans-serif",
        "canvas_background": "#07111f",
        "panel_background": "#101d2c",
        "panel_border": "#26384d",
        "text_primary": "#f4f7fb",
        "text_secondary": "#a9b7c8",
        "accent": "#36c2b4",
        "warning": "#f2b84b",
        "danger": "#ef6a6a",
        "title_font_size": 32,
        "body_font_size": 14,
        "number_precision": 0,
    }
)

_LIGHT_TOKENS = MappingProxyType(
    {
        "font_family": "Inter, system-ui, sans-serif",
        "canvas_background": "#f8fafc",
        "panel_background": "#ffffff",
        "panel_border": "#cbd5e1",
        "text_primary": "#0f172a",
        "text_secondary": "#475569",
        "accent": "#2563eb",
        "warning": "#d97706",
        "danger": "#dc2626",
        "title_font_size": 32,
        "body_font_size": 14,
        "number_precision": 0,
    }
)

_THEME_TOKENS = MappingProxyType({"dark": _DARK_TOKENS, "light": _LIGHT_TOKENS})


def _skeleton(
    id_: str,
    *,
    summary: int,
    main: int,
    secondary: int,
    sidebar: int,
    main_slot_weight: int = 2,
    sidebar_slot_weight: int = 1,
    gap: int = 16,
) -> TemplateSkeleton:
    return TemplateSkeleton(
        id=id_,
        region_columns=MappingProxyType(
            {
                "header": 1,
                "summary": summary,
                "main": main,
                "secondary": secondary,
                "sidebar": sidebar,
                "footer": 1,
            }
        ),
        region_slots=MappingProxyType(
            {
                "header": RegionSlot(0, 1, 0, 1),
                "summary": RegionSlot(1, 2, 0, 1),
                "main": RegionSlot(2, 6, 0, main_slot_weight),
                "sidebar": RegionSlot(2, 6, 1, sidebar_slot_weight),
                "secondary": RegionSlot(3, 3, 0, 1),
                "footer": RegionSlot(4, 1, 0, 1),
            }
        ),
        slot_gap=gap,
        safe_margin_x=48,
        safe_margin_y=32,
        title_height=64,
        theme_tokens=_THEME_TOKENS,
    )


TEMPLATE_SKELETONS: Mapping[str, TemplateSkeleton] = MappingProxyType(
    {
        "executive-overview": _skeleton(
            "executive-overview", summary=4, main=2, secondary=3, sidebar=1
        ),
        "trend-focus": _skeleton(
            "trend-focus",
            summary=3,
            main=1,
            secondary=2,
            sidebar=1,
            main_slot_weight=3,
        ),
        "comparison-board": _skeleton(
            "comparison-board", summary=4, main=2, secondary=2, sidebar=2
        ),
        "status-wall": _skeleton(
            "status-wall",
            summary=6,
            main=4,
            secondary=4,
            sidebar=2,
            main_slot_weight=1,
            sidebar_slot_weight=1,
            gap=12,
        ),
        "analysis-lab": _skeleton(
            "analysis-lab",
            summary=3,
            main=2,
            secondary=3,
            sidebar=1,
            main_slot_weight=5,
            sidebar_slot_weight=2,
        ),
    }
)


__all__ = ["RegionSlot", "TEMPLATE_SKELETONS", "TemplateSkeleton"]
