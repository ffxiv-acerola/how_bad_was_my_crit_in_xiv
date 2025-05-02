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
            "log_datetime",
            "fight",
            "kill time",
            "job",
            "player",
            "percentile",
            "analysis date",
            "analysis_id",
        ]
    )


def layout():
    """Display analysis history table with pagination and filtering."""
    columns = [
        {"name": "Link", "id": "link", "presentation": "markdown"},
        {"name": "Log date", "id": "log_datetime"},
        {"name": "Fight", "id": "fight"},
        {"name": "Kill time", "id": "kill time"},
        {"name": "Job", "id": "job"},
        {"name": "Player", "id": "player"},
        {
            "name": "Analysis\npercentile",  # Updated name
            "id": "percentile",
            "type": "numeric",
            "format": FormatTemplate.percentage(0),
        },
        {"name": "Analysis date", "id": "analysis date"},
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
            "whiteSpace": "pre-line",  # Allow line breaks in header
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
            html.P(
                "This page keeps track of all your previous analyses. "
                "You can filter/order the table by any column or click on the links to revisit your analyses."
            ),
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
                    },
                    {  # Ensure percentile header aligns text properly with line break
                        "if": {"column_id": "percentile"},
                        "whiteSpace": "pre-line",
                        "lineHeight": "1.2",
                        "verticalAlign": "middle",
                    },
                ],
                style_filter_conditional=[
                    {
                        "if": {"column_id": "job"},
                        "fontFamily": "sans-serif",
                        "fontSize": "1em",
                    }
                ],
                style_cell_conditional=[
                    # per-column style
                    {
                        "if": {"column_id": col},
                        "borderLeft": "none",
                        "borderRight": "none",
                        "fontFamily": "sans-serif",
                    }
                    for col in create_empty_dataframe().columns
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
                    },
                    # Add specific styling for link column to fix vertical alignment
                    {
                        "if": {"column_id": "link"},
                        "height": "50px",
                        "verticalAlign": "middle",
                    },
                ],
                # Don't need hidden columns anymore
                # Other table options
                cell_selectable=False,
                column_selectable=False,
                row_selectable=False,
                # The CSS is now moved to the external stylesheet
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
        # Sort the data by analysis_datetime in descending order (newest first)
        from datetime import datetime

        # Define a sorting function that can handle potential parsing errors
        def get_datetime_for_sorting(item):
            analysis_date = item.get("analysis_datetime", "")
            try:
                return datetime.strptime(analysis_date, "%Y-%m-%dT%H:%M:%S.%f")
            except (ValueError, TypeError):
                # Return a very old date for items that can't be parsed
                return datetime(1900, 1, 1)

        # Sort the list in place
        history_data.sort(key=get_datetime_for_sorting, reverse=True)

        # Convert from the API format to the expected format
        transformed_data = []
        for item in history_data:
            # Format the analysis date and log date as yyyy-mm-dd
            analysis_date = item.get("analysis_datetime", "")
            log_date = item.get("log_datetime", "")
            try:
                # Try to parse the dates and reformat them
                # Handle common date formats like "4/10/2025 11:30"
                parsed_analysis_date = datetime.strptime(
                    analysis_date, "%Y-%m-%dT%H:%M:%S.%f"
                )
                formatted_analysis_date = parsed_analysis_date.strftime(
                    "%Y-%m-%d %I:%M %p"
                )

                parsed_log_date = datetime.strptime(log_date, "%Y-%m-%dT%H:%M:%S.%f")
                formatted_log_date = parsed_log_date.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                # If parsing fails, keep the original format
                formatted_analysis_date = analysis_date
                formatted_log_date = log_date

            transformed_data.append(
                {
                    "link": item.get("analysis_scope", ""),
                    "log_datetime": formatted_log_date,
                    "analysis date": formatted_analysis_date,
                    "fight": item.get("encounter_short_name", ""),
                    "kill time": item.get("kill_time", ""),
                    "job": item.get("job", ""),
                    "player": item.get("player_name", ""),
                    "percentile": item.get("analysis_percentile", 0),
                    "analysis_id": item.get("analysis_id", ""),
                }
            )
        return transformed_data
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

    # Base conditional styling - simplified without parent/child hierarchy
    styles = [
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
        data = history_data.copy()  # Create a copy to avoid modifying the original
    else:
        data = pd.DataFrame(history_data).to_dict("records")

    # Convert link text to markdown format based on analysis type
    for row in data:
        analysis_id = row.get("analysis_id", "")
        link_text = row.get("link", "")

        # Determine the URL based on the link text
        if link_text == "Party Analysis":
            # For party analyses
            url = f"/party_analysis/{analysis_id}"
            link_text = "Party Analysis"
        else:
            # For individual player analyses
            url = f"/analysis/{analysis_id}"
            link_text = "Player analysis"

        # Create markdown format link
        row["link"] = f"[{link_text}]({url})"

    return data, styles
