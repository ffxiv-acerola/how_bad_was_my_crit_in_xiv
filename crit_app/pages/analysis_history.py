import dash
import pandas as pd
from dash import Input, Output, callback, dash_table, dcc, html
from dash.dash_table import FormatTemplate
from dash.exceptions import PreventUpdate

dash.register_page(
    __name__,
    path="/history",
)


def create_empty_dataframe():
    """Create empty dataframe with the correct schema."""
    return pd.DataFrame(
        columns=[
            "link",
            "analysis date",
            "fight",
            "kill time",
            "job",
            "player",
            "type",
            "percentile",
        ]
    )


def layout():
    """Display analysis history table with pagination and filtering."""
    columns = [
        {"name": "Link", "id": "link"},
        {"name": "Analysis date", "id": "analysis date"},
        {"name": "Fight", "id": "fight"},
        {"name": "Kill time", "id": "kill time"},
        {"name": "Job", "id": "job"},
        {"name": "Player", "id": "player"},
        {
            "name": "Percentile",
            "id": "percentile",
            "type": "numeric",
            "format": FormatTemplate.percentage(0),
        },
    ]

    # Create base styling for the table
    table_style = {
        "style_table": {"overflowX": "auto", "borderRadius": "5px"},
        "style_header": {
            "backgroundColor": "#222",
            "color": "white",
            "fontWeight": "bold",
            "textAlign": "left",
            "border": "none",
            "borderBottom": "1px solid #333",
            "fontFamily": "sans-serif",
        },
        "style_cell": {
            "backgroundColor": "#333",
            "color": "white",
            "textAlign": "left",
            "padding": "10px 15px",
            "fontFamily": "sans-serif",
            "border": "none",
            "borderBottom": "1px solid #292929",
            "userSelect": "none",
        },
        "style_data": {"borderBottomWidth": 0},
    }

    return html.Div(
        [
            html.H2("Analysis History", className="mb-4"),
            html.Hr(),
            # Store for loading data from app-level store
            dcc.Store(id="analysis-history-local", storage_type="memory"),
            dash_table.DataTable(
                id="history-data-table",
                columns=columns,
                data=create_empty_dataframe().to_dict(
                    "records"
                ),  # Start with empty table
                # Enable pagination with 25 rows per page
                page_size=25,
                page_action="native",
                # Enable filtering
                filter_action="native",
                # Enable sorting
                sort_action="native",
                sort_mode="multi",
                # Apply base styling
                **table_style,
                # Conditional styling will be applied via callback
                style_data_conditional=[],
                style_header_conditional=[
                    {
                        "if": {"column_id": "job"},
                        "fontFamily": "sans-serif",
                        "fontSize": "1em",
                    }
                ],
                style_filter_conditional=[
                    {
                        "if": {"column_id": "job"},
                        "fontFamily": "sans-serif",
                        "fontSize": "1em",
                    }
                ],
                style_cell_conditional=[
                    {
                        "if": {"column_id": col},
                        "borderLeft": "none",
                        "borderRight": "none",
                        "fontFamily": "sans-serif",
                    }
                    for col in create_empty_dataframe().columns
                    if col != "type"
                ]
                + [
                    {
                        "if": {"column_id": "job"},
                        "width": "60px",
                        "textAlign": "center",
                        "fontFamily": "job-icons",
                        "fontSize": "1.4em",
                        "paddingTop": "4px",
                        "paddingBottom": "4px",
                    }
                ],
                # Don't display the type column
                hidden_columns=["type"],
                # Other table options
                cell_selectable=False,
                column_selectable=False,
                row_selectable=False,
                # CSS for styling
                css=[
                    {
                        "selector": ".dash-spreadsheet",
                        "rule": "font-family: sans-serif; border-radius: 5px; overflow: hidden; box-shadow: 0 3px 6px rgba(0,0,0,0.16);",
                    },
                    # Hide the toggle columns button with CSS
                    {"selector": ".show-hide", "rule": "display: none !important;"},
                    # Soften the table appearance
                    {
                        "selector": ".dash-table-container .dash-spreadsheet td, .dash-table-container .dash-spreadsheet th",
                        "rule": "border-color: #292929 !important; ",
                    },
                    # Style the pagination controls
                    {
                        "selector": ".dash-table-container .previous-page, .dash-table-container .next-page, .dash-table-container .first-page, .dash-table-container .last-page",
                        "rule": "background-color: #333; color: white; border: none; border-radius: 3px;",
                    },
                    # Current page highlighting
                    {
                        "selector": ".dash-table-container .current-page",
                        "rule": "background-color: #333; color: white; border: none; border-radius: 3px;",
                    },
                    # Make filter text match table text color
                    {
                        "selector": ".dash-filter input::placeholder",
                        "rule": "color: white !important; opacity: 0.8;",
                    },
                    {
                        "selector": ".dash-filter input",
                        "rule": "color: white !important; background-color: #333 !important; border: 1px solid #444 !important;",
                    },
                    # Hide border on the last row to show rounded corners
                    {
                        "selector": ".dash-spreadsheet tr:last-child td",
                        "rule": "border-bottom: none !important;",
                    },
                    # Disable cell selection styling
                    {
                        "selector": ".dash-cell-value",
                        "rule": "caret-color: transparent !important;",
                    },
                    {
                        "selector": ".dash-spreadsheet td.dash-cell",
                        "rule": "border-color: #292929 !important; border-width: 0.5px !important;",
                    },
                    {
                        "selector": ".dash-spreadsheet tr td.dash-cell.focused",
                        "rule": "background-color: inherit !important; border-color: #292929 !important;",
                    },
                    {
                        "selector": ".dash-spreadsheet tr td.dash-cell.cell--selected",
                        "rule": "background-color: inherit !important; border-color: #292929 !important;",
                    },
                    # Ensure job column header and filter use default font at normal size with high specificity
                    {
                        "selector": '.dash-table-container [id^="header-job"], .dash-table-container [id^="job-filter"], .dash-table-container .column-header--job',
                        "rule": "font-family: sans-serif !important; font-size: 1em !important;",
                    },
                    # Style all non-job data cells with the default font
                    {
                        "selector": '.dash-table-container .dash-cell:not([data-dash-column="job"])',
                        "rule": "font-family: sans-serif !important;",
                    },
                    # Override job data cells with job-icons font and larger size
                    {
                        "selector": '.dash-table-container .dash-cell[data-dash-column="job"]',
                        "rule": "font-family: job-icons !important; font-size: 1.4em !important;",
                    },
                    # Ensure filter input for job column uses sans-serif with highest specificity
                    {
                        "selector": '.dash-table-container .dash-filter input[id^="job-filter"]',
                        "rule": "font-family: sans-serif !important; font-size: 1em !important;",
                    },
                ],
            ),
        ],
        className="container mt-4",
    )


@callback(
    Output("analysis-history-local", "data"),
    Input("analysis-history", "data"),
    prevent_initial_call=False,  # Allow initial call to handle data on first page load
)
def initialize_history_data(history_data):
    """Load data from the app-level store to the page-level store."""
    if not history_data:
        # If there's no history data in localStorage, return empty dataframe
        # This mimics a new user with no history
        return create_empty_dataframe().to_dict("records")

    # Check if we need to transform the data (if it's from an API/analysis)
    if (
        isinstance(history_data, list)
        and history_data
        and "analysis_scope" in history_data[0]
    ):
        # Convert from the API format to the expected format
        transformed_data = []
        for item in history_data:
            transformed_data.append(
                {
                    "link": item.get("analysis_scope", ""),
                    "analysis date": item.get("analysis_datetime", ""),
                    "fight": item.get("encounter_short_name", ""),
                    "kill time": item.get("kill_time", ""),
                    "job": item.get("job", ""),
                    "player": item.get("player_name", ""),
                    "percentile": item.get("analysis_percentile", 0),
                    "type": item.get("hierarchy", None),
                }
            )
        return transformed_data

    # If data is already in the correct format with expected keys
    if (
        isinstance(history_data, list)
        and history_data
        and all(key in history_data[0] for key in ["link", "analysis date", "fight"])
    ):
        return history_data

    return create_empty_dataframe().to_dict("records")


@callback(
    [
        Output("history-data-table", "data"),
        Output("history-data-table", "style_data_conditional"),
    ],
    Input("analysis-history-local", "data"),
)
def update_table_with_styling(history_data):
    """Update table with data and apply conditional styling based on the data."""
    if not history_data:
        raise PreventUpdate

    # Base conditional styling
    styles = [
        # Parent row styling
        {
            "if": {"filter_query": '{type} = "Parent"'},
            "backgroundColor": "#333",
            "borderTop": "2px solid #444",
            "borderBottom": "0px",
        },
        # Child row styling
        {
            "if": {"filter_query": '{type} = "Child"'},
            "backgroundColor": "#2a2a2a",
            "paddingLeft": "20px",
            "borderBottom": "1px solid #292929",
        },
        # Right align link field in child rows
        {
            "if": {"filter_query": '{type} = "Child"', "column_id": "link"},
            "textAlign": "right",
            "paddingRight": "15px",
        },
        # Apply job-icons font only to job column data cells
        {
            "if": {"column_id": "job"},
            "fontFamily": "job-icons",
            "fontSize": "1.4em",
            "paddingTop": "4px",
            "paddingBottom": "4px",
        },
        # Remove hover styling to prevent cell selection appearance
        {
            "if": {"state": "selected"},
            "backgroundColor": "inherit",
            "border": "inherit",
        },
    ]

    # Process data to records format
    if isinstance(history_data, list):
        data = history_data
    else:
        data = pd.DataFrame(history_data).to_dict("records")

    # Add styling for last child in each group
    df = (
        pd.DataFrame(data)
        if not isinstance(history_data, pd.DataFrame)
        else history_data
    )

    if not df.empty and "type" in df.columns:
        # Find indices of last child in each group
        last_child_indices = []
        for i in range(len(df)):
            if (
                i < len(df) - 1
                and df.iloc[i].get("type") == "Child"
                and df.iloc[i + 1].get("type") != "Child"
            ):
                last_child_indices.append(i)
            elif i == len(df) - 1 and df.iloc[i].get("type") == "Child":
                last_child_indices.append(i)

        # Add style for each last child
        for idx in last_child_indices:
            styles.append(
                {
                    "if": {
                        "filter_query": f'{{type}} = "Child" && {{row_index}} = {idx}'
                    },
                    "borderBottom": "2px solid #444",  # Darker border
                }
            )

    return data, styles
