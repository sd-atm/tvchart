from __future__ import annotations

import os
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import orjson
from dateutil import parser
from jinja2 import ChainableUndefined, Environment, FileSystemLoader
from pytz import UTC


class TVSeriesType(str, Enum):
    # https://tradingview.github.io/lightweight-charts/docs/series-types
    Area = "Area"
    Bar = "Bar"
    Baseline = "Baseline"
    Candlestick = "Candlestick"
    Histogram = "Histogram"
    Line = "Line"


class TVChart:
    def __init__(
        self, mode: str = "regular", chart_options: Dict[str, Any] = None
    ) -> None:
        """
        Args:
            mode (str): can be interday or regular
            chart_options (Dict[str, Any], optional): _description_. Defaults to None.
        """
        if mode.lower().strip() == "interday":
            if chart_options is None:
                chart_options = {}
            chart_options["timeScale"] = {"timeVisible": True, "secondsVisible": False}

        self.jinja_env = Environment(
            loader=FileSystemLoader(os.path.dirname(__file__) + os.sep + "templates"),
            undefined=ChainableUndefined,
        )
        self.time_series = None
        self.chart_options = chart_options
        self.series_markers: Dict[str, List[Dict[Any, Any]]] = {}
        self.legend_html = None
        self.__drawings = []

    def __fill_template(self, template: str, params: Dict[str, Any] = {}) -> str:
        return self.jinja_env.get_template(template).render(params)

    def set_legend_html(self, html: str) -> TVChart:
        """
        Set The Legend HTML Desplayed at top Left of the Page

        Args:
            html (str): Legend HTML

        Returns:
            TVRenderer: self
        """
        self.legend_html = html
        return self

    def add_ohlcv(
        self,
        t: List[Any],
        o: List[Any],
        h: List[Any],
        l: List[Any],
        c: List[Any],
        v: Optional[List[Any]] = None,
        ohlc_options: Optional[Dict[str, Any]] = None,
        volume_options: Optional[Dict[str, Any]] = None,
    ) -> TVChart:
        """
        Generate OHLC Figure

        Args:
            t (List[Any]): Time
            o (List[Any]): Open
            h (List[Any]): High
            l (List[Any]): Low
            c (List[Any]): Close
            v (Optional[List[Any]], optional): Volume. Defaults to None.
            ohlc_options (Optional[Dict[str, Any]], optional): Options for OHLC Chart refer . Defaults to None.
            volume_options (Optional[Dict[str, Any]], optional): Options for Volume Chart. Defaults to None.

        Returns:
            TVRenderer: self
        """
        self.time_series = [
            int(parser.parse(x).replace(tzinfo=UTC).timestamp()) for x in t
        ]
        ohlc_data = orjson.dumps(
            [
                {"time": x[0], "open": x[1], "high": x[2], "low": x[3], "close": x[4]}
                for x in zip(self.time_series, o, h, l, c)
            ]
        ).decode("utf-8")

        self.__drawings.append(
            self.__fill_template(
                "actions/add_series.html",
                {
                    "type": TVSeriesType.Candlestick.value,
                    "series_name": "ohlc",
                    "options": ohlc_options,
                    "data": ohlc_data,
                },
            )
        )

        if v:
            vdata = orjson.dumps(
                [
                    {
                        "time": x[0],
                        "value": x[1],
                    }
                    for x in zip(self.time_series, v)
                ]
            ).decode("utf-8")

            if not isinstance(volume_options, dict):
                volume_options = {}

            volume_options["priceFormat"] = {"type": "volume"}
            volume_options["priceScaleId"] = ""
            if "scaleMargins" not in volume_options:
                volume_options["scaleMargins"] = {"top": 0.9, "bottom": 0}
            if "color" not in volume_options:
                volume_options["color"] = "#26a69a"

            self.__drawings.append(
                self.__fill_template(
                    "actions/add_series.html",
                    {
                        "type": TVSeriesType.Histogram.value,
                        "series_name": "volume",
                        "options": volume_options,
                        "data": vdata,
                    },
                )
            )

        return self

    def add_series(
        self,
        name: str,
        pane: int,
        series: List[Any],
        type: TVSeriesType = TVSeriesType.Line,
        options: Dict[str, Any] = None,
    ) -> TVChart:
        """
        Add a Series
        Refer: https://tradingview.github.io/lightweight-charts/docs/series-types
        Args:
            type (TVSeriesType): Type of Series
            name (str): name of series
            pane (int): pane no starting from zero
            series (List[Any]): Series Data
            options (Dict[str, Any], optional): Series Option. Defaults to None.

        Returns:
            TVRenderer: self
        """
        if not isinstance(options, dict):
            options = {}
        options["pane"] = pane
        data = orjson.dumps(
            [
                {
                    "time": x[0],
                    "value": x[1],
                }
                for x in filter(
                    lambda i: i[1] is not None,
                    zip(self.time_series, series),
                )
            ]
        ).decode("utf-8")
        self.__drawings.append(
            self.__fill_template(
                "actions/add_series.html",
                {
                    "type": type.value,
                    "series_name": name,
                    "options": options,
                    "data": data,
                },
            )
        )
        return self

    def add_price_line(
        self,
        name: str,
        price: float,
        color: str,
        line_width: int = 2,
        line_style: int = 2,
        axis_label_visiable: bool = True,
        title: str = None,
    ) -> TVChart:
        """
        Added A Horizontal Price Line
        https://tradingview.github.io/lightweight-charts/tutorials/how_to/price-line

        Args:
            name (str): name of the seires
            price (float): price
            color (str): string color
            line_width (int, optional): Line width Defaults to 2.
            line_style (int, optional): Line Style Defaults to 2.
            axis_label_visiable (bool, optional): _description_. Defaults to True.
            title (str, optional): title of the line. Defaults to None.

        Returns:
            TVRenderer: _description_
        """
        data = orjson.dumps(
            {
                "price": price,
                "color": color,
                "lineWidth": line_width,
                "lineStyle": line_style,
                "axisLabelVisible": axis_label_visiable,
                "title": title,
            }
        ).decode("utf-8")
        self.__drawings.append(
            self.__fill_template(
                "actions/add_priceline.html",
                {"series_name": name, "data": data},
            )
        )
        return self

    def add_markers_by_idx(
        self,
        name: str,
        idx_dict: Dict[int, str],
        options: Dict[str, str] = {
            "color": "red",
            "shape": "arrowUp",
            "position": "belowBar",
        },
    ) -> TVChart:
        """
        Add Markers to series
        https://tradingview.github.io/lightweight-charts/tutorials/how_to/series-markers
        Args:
            name (str): name of series
            idx_dict (Dict[int, str]): Dict of index : text for the markers
            options (Dict[str, str]): Must include color, shape, position. Defaults to Dict[str, str].

        Returns:
            TVRenderer: self
        """
        return self.add_markers_by_time(
            name=name,
            time_dict={self.time_series[k]: v for k, v in idx_dict.items()},
            options=options,
        )

    def add_markers_by_time(
        self,
        name: str,
        time_dict: Dict[Any, str],
        options: Dict[str, str] = {
            "color": "red",
            "shape": "arrowUp",
            "position": "belowBar",
        },
    ) -> TVChart:
        """
        Similer to add marker by index

        Args:
            name (str): _description_
            time_dict (Dict[Any, str]): _description_
            options (_type_, optional): _description_. Defaults to { "color": "red", "shape": "arrowUp", "position": "belowBar", }.

        Returns:
            TVRenderer: _description_
        """
        self.series_markers[name] = self.series_markers.get(name, [])
        self.series_markers[name] += [
            {"time": k, "text": v, **options} for k, v in time_dict.items()
        ]
        return self

    def add_lines_by_idx(
        self,
        name: str,
        pane: int,
        idx_lines: List[Tuple[int, float, int, float]],
        type: TVSeriesType = TVSeriesType.Line,
        options: Dict[str, Any] = None,
    ) -> TVChart:
        """
        Add Horizontal Lines

        Args:
            name (str): _description_
            pane (int): _description_
            idx_lines (List[Tuple[int, float, int, float]]): _description_
            type (TVSeriesType, optional): _description_. Defaults to TVSeriesType.Line.
            options (Dict[str, Any], optional): _description_. Defaults to None.

        Returns:
            TVRenderer: _description_
        """
        return self.add_lines_by_time(
            name=name,
            pane=pane,
            time_lines=[
                (self.time_series[x1], y1, self.time_series[x2], y2)
                for x1, y1, x2, y2 in idx_lines
            ],
            type=type,
            options=options,
        )

    def add_lines_by_time(
        self,
        name: str,
        pane: int,
        time_lines: List[Tuple[Any, float, Any, float]],
        type: TVSeriesType = TVSeriesType.Line,
        options: Dict[str, Any] = None,
    ) -> TVChart:
        if not isinstance(options, dict):
            options = {}
        for idx, [x1, y1, x2, y2] in enumerate(time_lines):
            data = orjson.dumps(
                [{"time": x1, "value": y1}, {"time": x2, "value": y2}]
            ).decode("utf-8")
            options["pane"] = pane
            self.__drawings.append(
                self.__fill_template(
                    "actions/add_series.html",
                    {
                        "type": type.value,
                        "series_name": f"{name}{idx}",
                        "options": options,
                        "data": data,
                    },
                )
            )
        return self

    def html(self) -> str:
        for name, data in self.series_markers.items():
            self.__drawings.append(
                self.__fill_template(
                    "actions/add_markers.html",
                    {"series_name": name, "data": orjson.dumps(data).decode("utf-8")},
                )
            )
        content = self.__fill_template(
            "index.html",
            {
                "chart_options": self.chart_options,
                "legend_html": self.legend_html,
                "drawings": "\n\n".join(self.__drawings),
            },
        )
        return content

    def save(self, file_path: str):
        content = self.html()
        with open(file_path, "w") as f:
            f.write(content)
