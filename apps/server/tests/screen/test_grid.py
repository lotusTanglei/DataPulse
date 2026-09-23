import pytest

from datapulse.screen.grid import GridCell, GridSystem


@pytest.mark.parametrize("columns", [12, 24])
def test_grid_maps_cells_with_safe_margin_and_gutters(columns: int) -> None:
    grid = GridSystem(
        canvas_width=1920,
        canvas_height=1080,
        columns=columns,
        rows=12,
        margin=48,
        gutter=16,
    )

    first = grid.frame(GridCell(column=0, row=0, column_span=columns // 2, row_span=3))
    second = grid.frame(
        GridCell(column=columns // 2, row=0, column_span=columns // 2, row_span=3)
    )

    assert first.x == 48
    assert first.y == 48
    assert first.x + first.width + 16 == second.x
    assert second.x + second.width == 1872
    assert first.height > 0


def test_grid_rejects_cells_outside_the_configured_partition() -> None:
    grid = GridSystem(canvas_width=1920, canvas_height=1080, columns=24, rows=12)

    with pytest.raises(ValueError, match="grid bounds"):
        grid.frame(GridCell(column=20, row=0, column_span=5, row_span=1))
