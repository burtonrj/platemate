from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

import pandas as pd


class WellStatistic:
    def __init__(self, datatype: str, variable: str, value: Union[int, float]):
        self.datatype = datatype
        self.variable = variable
        self.value = value

    def __repr__(self):
        return f"WellStatistic(datatype={self.datatype}, variable={self.variable}, value={self.value})"

    def as_dict(self) -> Dict[str, Any]:
        return {"datatype": self.datatype, "variable": self.variable, "value": self.value}


class WellStatisticList(List[WellStatistic]):
    def search(self, datatype: Optional[str] = None, variable: Optional[str] = None) -> List[WellStatistic]:
        if datatype is not None:
            if variable is not None:
                return [ws for ws in self if ws.datatype == datatype and ws.variable == variable]
            return [ws for ws in self if ws.datatype == datatype]
        if variable is not None:
            return [ws for ws in self if ws.variable == variable]
        raise ValueError("Must provide either datatype or variable or both")


class Well:
    def __init__(
        self, location: str, sample_id: str, data: WellStatisticList, standard: bool = False, background: bool = False
    ):
        self.location: Union[int, None]
        self.location_str = location
        self.sample_id = sample_id
        self.data = data
        self.standard = standard
        self.background = background
        try:
            self.location = int(re.search(r"(\d+).*", location).group(1))  # type: ignore
        except (IndexError, ValueError):
            self.location = None

    @classmethod
    def from_series(
        cls,
        row: pd.Series,
        datatype: str,
        standard_pattern: Optional[str] = "[Ss]tandard[0-9]+",
        background_pattern: Optional[str] = "[Bb]ackground[0-9]+",
    ):
        variables = [i for i in row.index if i not in ["Location", "Sample"]]
        data = WellStatisticList([WellStatistic(datatype=datatype, variable=var, value=row[var]) for var in variables])
        return cls(
            location=row.Location,
            sample_id=row.Sample,
            data=data,
            standard=re.match(standard_pattern, row.Sample) is not None,  # type: ignore
            background=re.match(background_pattern, row.Sample) is not None,  # type: ignore
        )


def _plate_from_dataframe(
    data: pd.DataFrame,
    standard_pattern: Optional[str] = "[Ss]tandard[0-9]+",
    background_pattern: Optional[str] = "[Bb]ackground[0-9]+",
):
    return [
        Well.from_series(
            row=row,
            datatype="fluorescence intensity",
            standard_pattern=standard_pattern,
            background_pattern=background_pattern,
        )
        for _, row in data.iterrows()
    ]


class Plate:
    def __init__(
        self,
        data: List[Well],
        filepath: Optional[str] = None,
        run_datetime: Optional[str] = None,
        batch_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ):
        self.data = data
        self.filepath = filepath
        self.run_datetime = run_datetime
        self.batch_id = batch_id
        self.meta = meta

    @classmethod
    def from_dataframe(
        cls,
        data: pd.DataFrame,
        run_datetime: Optional[str] = None,
        batch_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        standard_pattern: Optional[str] = "[Ss]tandard[0-9]+",
        background_pattern: Optional[str] = "[Bb]ackground[0-9]+",
    ):
        return cls(
            data=_plate_from_dataframe(
                data=data, standard_pattern=standard_pattern, background_pattern=background_pattern
            ),
            filepath=None,
            run_datetime=run_datetime,
            batch_id=batch_id,
            meta=meta,
        )

    @classmethod
    def from_csv(
        cls,
        filepath: str,
        run_datetime: Optional[str] = None,
        batch_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        standard_pattern: Optional[str] = "[Ss]tandard[0-9]+",
        background_pattern: Optional[str] = "[Bb]ackground[0-9]+",
    ):
        return cls(
            data=_plate_from_dataframe(
                data=pd.read_csv(filepath), standard_pattern=standard_pattern, background_pattern=background_pattern
            ),
            filepath=filepath,
            run_datetime=run_datetime,
            batch_id=batch_id,
            meta=meta,
        )

    @classmethod
    def from_excel(
        cls,
        filepath: str,
        run_datetime: Optional[str] = None,
        batch_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        standard_pattern: Optional[str] = "[Ss]tandard[0-9]+",
        background_pattern: Optional[str] = "[Bb]ackground[0-9]+",
        **kwargs,
    ):
        return cls(
            data=_plate_from_dataframe(
                data=pd.read_excel(filepath, **kwargs),
                standard_pattern=standard_pattern,
                background_pattern=background_pattern,
            ),
            filepath=filepath,
            run_datetime=run_datetime,
            batch_id=batch_id,
            meta=meta,
        )

    def __sub__(self, other: Plate):
        pass

    def add_filter(self):
        pass

    def plot_cv(self):
        pass


class Luminex(Plate):
    def plot_bead_count(self):
        pass


def _ref_from_dataframe(data: pd.DataFrame):
    try:
        return {x['analyte']: {k: v for k, v in x.items() if k != 'analyte'} for x in data.to_dict("records")}
    except KeyError:
        raise KeyError("Dataframe must contain the column 'analyte'")


class Reference:
    def __init__(self, data: Optional[dict] = None):
        self.data = data or defaultdict(dict)

    @classmethod
    def from_dataframe(cls, data: pd.DataFrame):
        return cls(data=_ref_from_dataframe(data=data))

    @classmethod
    def from_csv(cls, filepath: str):
        return cls(data=_ref_from_dataframe(data=pd.read_csv(filepath)))

    @classmethod
    def from_excel(cls, filepath: str, **kwargs):
        return cls(data=_ref_from_dataframe(data=pd.read_excel(filepath, **kwargs)))

    def put(self, analyte: str, standard: str, value: float):
        self.data[analyte][standard] = value

    def get(self, analyte: Optional[str] = None, standard: Optional[str] = None) -> Union[float, pd.Series]:
        try:
            if analyte is not None:
                if standard is not None:
                    return self.data[analyte][standard]
                return pd.Series(self.data[analyte])
            if standard is not None:
                data = {a: self.data[a][standard] for a in self.data.keys()}
                return pd.Series(data)
            raise ValueError("Must provide either analyte, standard, or both")
        except KeyError:
            raise KeyError("Invalid analyte/standard, does not exist.")

    def dataframe(self):
        return pd.DataFrame(self.data).T
