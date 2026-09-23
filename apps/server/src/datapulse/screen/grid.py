from pydantic import Field

from datapulse.contracts.common import ContractModel, PositiveFloat, PositiveInt
from datapulse.contracts.dashboard import Frame


class GridCell(ContractModel):
    column: int = Field(ge=0)
    row: int = Field(ge=0)
    column_span: PositiveInt
    row_span: PositiveInt
    z_index: int = 0


class GridSystem:
    def __init__(
        self,
        *,
        canvas_width: PositiveFloat,
        canvas_height: PositiveFloat,
        columns: int,
        rows: int,
        margin: float = 48,
        gutter: float = 16,
    ) -> None:
        if columns not in {12, 24}:
            raise ValueError("grid columns must be 12 or 24")
        if rows < 1:
            raise ValueError("grid rows must be positive")
        usable_width = canvas_width - margin * 2 - gutter * (columns - 1)
        usable_height = canvas_height - margin * 2 - gutter * (rows - 1)
        if usable_width <= 0 or usable_height <= 0:
            raise ValueError("grid has no usable area")
        self.columns = columns
        self.rows = rows
        self.margin = margin
        self.gutter = gutter
        self._column_width = usable_width / columns
        self._row_height = usable_height / rows

    @staticmethod
    def _rounded(value: float) -> float:
        return round(value, 4)

    def frame(self, cell: GridCell) -> Frame:
        if cell.column + cell.column_span > self.columns or cell.row + cell.row_span > self.rows:
            raise ValueError("cell exceeds grid bounds")
        x = self.margin + cell.column * (self._column_width + self.gutter)
        y = self.margin + cell.row * (self._row_height + self.gutter)
        width = cell.column_span * self._column_width + (cell.column_span - 1) * self.gutter
        height = cell.row_span * self._row_height + (cell.row_span - 1) * self.gutter
        return Frame(
            x=self._rounded(x),
            y=self._rounded(y),
            width=self._rounded(width),
            height=self._rounded(height),
            z_index=cell.z_index,
        )


__all__ = ["GridCell", "GridSystem"]
