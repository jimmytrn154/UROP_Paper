import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash_cytoscape as cyto
import requests

# Initialize the Dash app
app = dash.Dash(__name__)

# Internal CSS styling
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
    "input": {
        "width": "100%",
        "padding": "10px",
        "marginBottom": "10px",
        "border": "1px solid #ccc",
        "borderRadius": "5px"
    },
    "button": {
        "display": "block",
        "width": "100%",
        "padding": "10px",
        "backgroundColor": "#007BFF",
        "color": "#fff",
        "border": "none",
        "borderRadius": "5px",
        "cursor": "pointer"
    },
    "button:hover": {
        "backgroundColor": "#0056b3"
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

# Base cytoscape stylesheet
cytoscape_stylesheet = [
    {"selector": ".node-keyword", "style": {"label": "data(label)", "background-color": "#FF5733"}},
    {"selector": ".node-restaurant", "style": {"label": "data(label)", "background-color": "#33FF57"}}
]

# Layout for the Dash app
app.layout = html.Div(style=internal_styles["container"], children=[
    html.H1("Keyword-Restaurant Relationships", style=internal_styles["header"]),

    # Dropdowns (placeholders for model options)
    html.Div(
        style={"display": "flex", "justifyContent": "space-between", "marginBottom": "20px"},
        children=[
            dcc.Dropdown(
                id="rec-model",
                options=[],  # Add your options here
                placeholder="Rec model",
                style={"width": "80%"}
            ),
            dcc.Dropdown(
                id="retrieval-model",
                options=[],  # Add your options here
                placeholder="Retrieval model",
                style={"width": "80%"}
            ),
            dcc.Dropdown(
                id="rerank-model",
                options=[],  # Add your options here
                placeholder="re-rank model",
                style={"width": "80%"}
            ),
            dcc.Dropdown(
                id="sort-by",
                options=[],  # Add your options here
                placeholder="sort by",
                style={"width": "80%"}
            )
        ]
    ),

    # Search bar and button
    html.Div([
        dcc.Input(
            id="keyword-input",
            type="text",
            placeholder="Enter keywords, separated by commas",
            style=internal_styles["input"]
        ),
        html.Button("Search", id="search-button", style=internal_styles["button"]),
    ]),
    html.Div(id="popup-container", style={"position": "relative"}),
    cyto.Cytoscape(
        id="cytoscape-graph",
        layout={"name": "circle"},
        stylesheet=cytoscape_stylesheet,
        style=internal_styles["graph"],
        elements=[]
    )
])

def compute_dynamic_yellow(connection_count):
    """
    Returns a hex color based on the number of keyword connections.
    For connection_count == 2: base yellow (#FFD700)
    For 3: lighter yellow (#FFEC8B)
    For 4: even lighter yellow (#FFF68F)
    For 5 or more: lightest yellow (#FFF8DC)
    """
    if connection_count == 2:
        return "#FFEC8B"  # Base yellow
    elif connection_count == 3:
        return "#FFD700"
    elif connection_count == 4:
        return "#FFF68F"
    elif connection_count >= 5:
        return "#FFF8DC"
    else:
        return "#33FF57"  # Fallback for non-special nodes

# Callback to update the graph based on selected keywords
@app.callback(
    [Output("cytoscape-graph", "elements"), Output("keyword-input", "value")],
    Input("search-button", "n_clicks"),
    State("keyword-input", "value")
)
def update_graph(n_clicks, keyword_input):
    if not keyword_input:
        return [], ""
    
    # Split keywords by comma and trim spaces
    selected_keywords = [kw.strip() for kw in keyword_input.split(",")]
    
    # Request the filtered data from the Flask backend
    response = requests.get(
        "http://127.0.0.1:5000/get_restaurant_keywords",
        params={"keywords": selected_keywords}
    )
    filtered_edges_with_flags = response.json()
    
    # Compute connection count for each restaurant
    restaurant_counts = {}
    for edge in filtered_edges_with_flags:
        restaurant = edge["restaurant"]
        restaurant_counts[restaurant] = restaurant_counts.get(restaurant, 0) + 1
    
    # Convert edges to Cytoscape elements
    elements = []
    added_nodes = set()
    for edge in filtered_edges_with_flags:
        keyword = edge["keyword"]
        restaurant = edge["restaurant"]
        
        # Add keyword node
        if keyword not in added_nodes:
            elements.append({
                "data": {"id": keyword, "label": keyword},
                "classes": "node-keyword"
            })
            added_nodes.add(keyword)
        
        # Add restaurant node with dynamic color if it's special (connection count > 1)
        if restaurant not in added_nodes:
            count = restaurant_counts.get(restaurant, 0)
            if count > 1:
                dynamic_color = compute_dynamic_yellow(count)
                node_style = {"label": f"Restaurant {restaurant[:5]}", "background-color": dynamic_color}
                elements.append({
                    "data": {"id": restaurant, "label": f"Restaurant {restaurant[:5]}"},
                    "style": node_style
                })
            else:
                elements.append({
                    "data": {"id": restaurant, "label": f"Restaurant {restaurant[:5]}"},
                    "classes": "node-restaurant"
                })
            added_nodes.add(restaurant)
        
        # Add the edge connecting keyword and restaurant
        elements.append({
            "data": {"source": keyword, "target": restaurant}
        })
    
    return elements, ", ".join(selected_keywords)

# Callback to display popup on restaurant node click
@app.callback(
    Output("popup-container", "children"),
    [Input("cytoscape-graph", "tapNode")],
    [State("keyword-input", "value")]
)
def display_popup(tap_node, current_keywords):
    if not tap_node or "node-restaurant" not in tap_node.get("classes", ""):
        return []
    
    node_id = tap_node["data"]["id"]
    node_label = tap_node["data"]["label"]
    
    popup = html.Div(
        style={**internal_styles["popup"], "left": f"{tap_node['position']['x']}px", "top": f"{tap_node['position']['y']}px"},
        children=[
            html.H3(f"User comments for {node_label}", style={"margin": "0 0 10px", "fontSize": "20px"}),
            html.H3("User 1", style={"margin": "20px 0 10px", "fontSize": "16px"}),
            html.P(f"I love the style of {current_keywords} here, it is absolutely unique!", style={"margin": "0", "fontSize": "14px"}),
            html.H3("User 2", style={"margin": "20px 0 10px", "fontSize": "16px"}),
            html.P(f"The {current_keywords} here is undoubtedly a must-to-try!", style={"margin": "0", "fontSize": "14px"}),
            html.H3("User 3", style={"margin": "20px 0 10px", "fontSize": "16px"}),
            html.P(f"The chef definitely has a treasured {current_keywords}'s recipe!", style={"margin": "0", "fontSize": "14px"}),
        ]
    )
    
    return popup

if __name__ == "__main__":
    app.run_server(debug=True, port=8050)
