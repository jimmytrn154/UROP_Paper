import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash_cytoscape as cyto
import requests
from collections import defaultdict

# Initialize the Dash app
app = dash.Dash(__name__)

# ------------------------------------------------------------------------------
# Internal CSS Styling with Flexbox Layout
# ------------------------------------------------------------------------------
internal_styles = {
    "container": {
        "fontFamily": "Arial, sans-serif",
        "padding": "20px",
        "maxWidth": "800px",
        "margin": "0 auto"
    },
    "header": {
        "textAlign": "center",
        "color": "#333",
        "marginBottom": "20px"
    },
    # A generic row style for horizontally aligned items
    "row": {
        "display": "flex",
        "flexWrap": "wrap",
        "alignItems": "center",
        "justifyContent": "space-between",
        "gap": "10px",
        "marginBottom": "20px"
    },
    # Each dropdown in the row can expand/shrink as needed
    "dropdown": {
        "flex": "1",
        "minWidth": "150px"
    },
    # Specifically for the max-restaurant dropdown (if you want a fixed width)
    "dropdownMaxRest": {
        "width": "200px"
    },
    # Container for search input and button
    "searchContainer": {
        "display": "flex",
        "alignItems": "center",
        "gap": "10px",
        "marginBottom": "20px"
    },
    "input": {
        "flex": "1",
        "padding": "10px",
        "border": "1px solid #ccc",
        "borderRadius": "5px"
    },
    "button": {
        "padding": "10px 20px",
        "backgroundColor": "#007BFF",
        "color": "#fff",
        "border": "none",
        "borderRadius": "5px",
        "cursor": "pointer"
    },
    "graph": {
        "width": "100%",
        "height": "600px",
        "border": "1px solid #ddd",
        "borderRadius": "5px",
        "boxShadow": "0 2px 4px rgba(0, 0, 0, 0.1)"
    },
    "popup": {
        "position": "absolute",
        "zIndex": 10,
        "backgroundColor": "#FFFFFF",
        "border": "1px solid #CCC",
        "borderRadius": "5px",
        "padding": "10px",
        "boxShadow": "0 4px 8px rgba(0, 0, 0, 0.2)",
        "width": "200px",
        "transition": "opacity 0.3s ease-in-out",
    }
}

# ------------------------------------------------------------------------------
# Cytoscape Stylesheet
# ------------------------------------------------------------------------------
cytoscape_stylesheet = [
    {"selector": ".node-keyword", "style": {"label": "data(label)", "background-color": "#FF5733"}},
    {"selector": ".node-restaurant", "style": {"label": "data(label)", "background-color": "#33FF57"}}
]

# ------------------------------------------------------------------------------
# App Layout
# ------------------------------------------------------------------------------
app.layout = html.Div(style=internal_styles["container"], children=[

    html.H1("Keyword-Restaurant Relationships", style=internal_styles["header"]),

    # Row of 4 dropdowns for models
    html.Div(style=internal_styles["row"], children=[
        dcc.Dropdown(
            id="rec-model",
            options=[],  # Add your options here
            placeholder="Rec model",
            style=internal_styles["dropdown"]
        ),
        dcc.Dropdown(
            id="retrieval-model",
            options=[],  # Add your options here
            placeholder="Retrieval model",
            style=internal_styles["dropdown"]
        ),
        dcc.Dropdown(
            id="rerank-model",
            options=[],  # Add your options here
            placeholder="re-rank model",
            style=internal_styles["dropdown"]
        ),
        dcc.Dropdown(
            id="sort-by",
            options=[],  # Add your options here
            placeholder="sort by",
            style=internal_styles["dropdown"]
        )
    ]),

    # Dropdown to limit the number of restaurants per keyword
    html.Div(style=internal_styles["row"], children=[
        dcc.Dropdown(
            id="max-restaurant-dropdown",
            options=[{"label": str(i), "value": i} for i in [5, 10, 15, 20]],
            placeholder="Max Restaurants",
            value=10,  # Default to 10
            style=internal_styles["dropdownMaxRest"]
        )
    ]),

    # Search input + button in a single row
    html.Div(style=internal_styles["searchContainer"], children=[
        dcc.Input(
            id="keyword-input",
            type="text",
            placeholder="Enter keywords, separated by commas",
            style=internal_styles["input"]
        ),
        html.Button("Search", id="search-button", style=internal_styles["button"])
    ]),

    # Container for the popup
    html.Div(id="popup-container", style={"position": "relative"}),

    # Cytoscape graph
    cyto.Cytoscape(
        id="cytoscape-graph",
        layout={"name": "circle"},
        stylesheet=cytoscape_stylesheet,
        style=internal_styles["graph"],
        elements=[]
    )
])

# ------------------------------------------------------------------------------
# compute_dynamic_yellow: color logic for multi-connection restaurants
# ------------------------------------------------------------------------------
def compute_dynamic_yellow(connection_count):
    """
    Returns a hex color based on the number of keyword connections.
    For connection_count == 2: #FFEC8B
    For 3: #FFD700
    For 4: #FFF68F
    For 5 or more: #FFF8DC
    Otherwise: #33FF57 (fallback)
    """
    if connection_count == 2:
        return "#FFEC8B"
    elif connection_count == 3:
        return "#FFD700"
    elif connection_count == 4:
        return "#FFF68F"
    elif connection_count >= 5:
        return "#FFF8DC"
    else:
        return "#33FF57"  # Fallback color

# ------------------------------------------------------------------------------
# Callback: Update the graph based on selected keywords & max restaurants
# ------------------------------------------------------------------------------
@app.callback(
    [Output("cytoscape-graph", "elements"), Output("keyword-input", "value")],
    [Input("search-button", "n_clicks")],
    [State("keyword-input", "value"), State("max-restaurant-dropdown", "value")]
)
def update_graph(n_clicks, keyword_input, max_rest):
    if not keyword_input:
        return [], ""

    # Split keywords by comma and trim spaces
    selected_keywords = [kw.strip() for kw in keyword_input.split(",")]

    # Request filtered data from your Flask backend
    response = requests.get(
        "http://127.0.0.1:5000/get_restaurant_keywords",
        params={"keywords": selected_keywords}
    )
    # Example response: [{"keyword": "pizza", "restaurant": "PizzaHut"}, ...]

    filtered_edges = response.json()

    # Group edges by keyword
    keyword_rest_dict = defaultdict(list)
    for edge in filtered_edges:
        keyword_rest_dict[edge["keyword"]].append(edge)

    # For each keyword, slice the list of restaurants to 'max_rest'
    limited_edges = []
    for kw, edges_list in keyword_rest_dict.items():
        limited_edges.extend(edges_list[:max_rest])

    # Recompute restaurant connection counts based on the limited edges
    restaurant_counts = {}
    for edge in limited_edges:
        restaurant = edge["restaurant"]
        restaurant_counts[restaurant] = restaurant_counts.get(restaurant, 0) + 1

    # Convert limited edges to Cytoscape elements
    elements = []
    added_nodes = set()
    for edge in limited_edges:
        keyword = edge["keyword"]
        restaurant = edge["restaurant"]

        # Add keyword node if not added yet
        if keyword not in added_nodes:
            elements.append({
                "data": {"id": keyword, "label": keyword},
                "classes": "node-keyword"
            })
            added_nodes.add(keyword)

        # Add restaurant node with dynamic color if count > 1
        if restaurant not in added_nodes:
            count = restaurant_counts[restaurant]
            if count > 1:
                dynamic_color = compute_dynamic_yellow(count)
                node_style = {
                    "label": f"Restaurant {restaurant[:5]}",
                    "background-color": dynamic_color
                }
                elements.append({
                    "data": {"id": restaurant, "label": f"Restaurant {restaurant[:5]}"},
                    "style": node_style
                })
            else:
                # Single connection => default green
                elements.append({
                    "data": {"id": restaurant, "label": f"Restaurant {restaurant[:5]}"},
                    "classes": "node-restaurant"
                })
            added_nodes.add(restaurant)

        # Add edge
        elements.append({
            "data": {"source": keyword, "target": restaurant}
        })

    # Return the new graph elements and reconstruct the keyword input
    return elements, ", ".join(selected_keywords)

# ------------------------------------------------------------------------------
# Callback: Display popup on restaurant node click
# ------------------------------------------------------------------------------
@app.callback(
    Output("popup-container", "children"),
    [Input("cytoscape-graph", "tapNode")],
    [State("keyword-input", "value")]
)
def display_popup(tap_node, current_keywords):
    # If there's no node or it's not a restaurant node, don't show popup
    if not tap_node or "node-restaurant" not in tap_node.get("classes", ""):
        return []

    node_label = tap_node["data"]["label"]

    # Example popup content
    popup = html.Div(
        style={
            **internal_styles["popup"],
            "left": f"{tap_node['position']['x']}px",
            "top": f"{tap_node['position']['y']}px"
        },
        children=[
            html.H3(f"User comments for {node_label}", 
                    style={"margin": "0 0 10px", "fontSize": "20px"}),
            html.H3("User 1", style={"margin": "20px 0 10px", "fontSize": "16px"}),
            html.P(f"I love the style of {current_keywords} here, it is absolutely unique!", 
                   style={"margin": "0", "fontSize": "14px"}),
            html.H3("User 2", style={"margin": "20px 0 10px", "fontSize": "16px"}),
            html.P(f"The {current_keywords} here is undoubtedly a must-to-try!", 
                   style={"margin": "0", "fontSize": "14px"}),
            html.H3("User 3", style={"margin": "20px 0 10px", "fontSize": "16px"}),
            html.P(f"The chef definitely has a treasured {current_keywords}'s recipe!", 
                   style={"margin": "0", "fontSize": "14px"}),
        ]
    )
    return popup

if __name__ == "__main__":
    app.run_server(debug=True, port=8050)
