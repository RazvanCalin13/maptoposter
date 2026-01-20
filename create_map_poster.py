# -*- coding: utf-8 -*-
import osmnx as ox
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import matplotlib.colors as mcolors
import numpy as np
from geopy.geocoders import Nominatim
from tqdm import tqdm
import time
import json
import os
import sys
import pickle
import hashlib
from datetime import datetime
import argparse
from matplotlib.path import Path
from matplotlib.patches import PathPatch


# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

THEMES_DIR = "themes"
FONTS_DIR = "fonts"
POSTERS_DIR = "posters"
CACHE_DIR = "cache"

def load_fonts():
    """
    Load Roboto fonts from the fonts directory.
    Returns dict with font paths for different weights.
    """
    fonts = {
        'bold': os.path.join(FONTS_DIR, 'Roboto-Bold.ttf'),
        'regular': os.path.join(FONTS_DIR, 'Roboto-Regular.ttf'),
        'light': os.path.join(FONTS_DIR, 'Roboto-Light.ttf')
    }
    
    # Verify fonts exist
    for weight, path in fonts.items():
        if not os.path.exists(path):
            print(f"⚠ Font not found: {path}")
            return None
    
    return fonts

FONTS = load_fonts()

def generate_output_filename(city, theme_name):
    """
    Generate unique output filename with city, theme, and datetime.
    """
    if not os.path.exists(POSTERS_DIR):
        os.makedirs(POSTERS_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    city_slug = city.lower().replace(' ', '_')
    filename = f"{city_slug}_{theme_name}_{timestamp}.png"
    return os.path.join(POSTERS_DIR, filename)

def get_available_themes():
    """
    Scans the themes directory and returns a list of available theme names.
    """
    if not os.path.exists(THEMES_DIR):
        os.makedirs(THEMES_DIR)
        return []
    
    themes = []
    for file in sorted(os.listdir(THEMES_DIR)):
        if file.endswith('.json'):
            theme_name = file[:-5]  # Remove .json extension
            themes.append(theme_name)
    return themes

def load_theme(theme_name="feature_based"):
    """
    Load theme from JSON file in themes directory.
    """
    theme_file = os.path.join(THEMES_DIR, f"{theme_name}.json")
    
    if not os.path.exists(theme_file):
        print(f"⚠ Theme file '{theme_file}' not found. Using default feature_based theme.")
        # Fallback to embedded default theme
        return {
            "name": "Feature-Based Shading",
            "bg": "#FFFFFF",
            "text": "#000000",
            "gradient_color": "#FFFFFF",
            "water": "#C0C0C0",
            "parks": "#F0F0F0",
            "road_motorway": "#0A0A0A",
            "road_primary": "#1A1A1A",
            "road_secondary": "#2A2A2A",
            "road_tertiary": "#3A3A3A",
            "road_residential": "#4A4A4A",
            "road_default": "#3A3A3A"
        }
    
    with open(theme_file, 'r') as f:
        theme = json.load(f)
        print(f"✓ Loaded theme: {theme.get('name', theme_name)}")
        if 'description' in theme:
            print(f"  {theme['description']}")
        return theme

# Load theme (can be changed via command line or input)
THEME = None  # Will be loaded later

def create_gradient_fade(ax, color, location='bottom', zorder=10):
    """
    Creates a fade effect at the top or bottom of the map.
    """
    vals = np.linspace(0, 1, 256).reshape(-1, 1)
    gradient = np.hstack((vals, vals))
    
    rgb = mcolors.to_rgb(color)
    my_colors = np.zeros((256, 4))
    my_colors[:, 0] = rgb[0]
    my_colors[:, 1] = rgb[1]
    my_colors[:, 2] = rgb[2]
    
    if location == 'bottom':
        my_colors[:, 3] = np.linspace(1, 0, 256)
        extent_y_start = 0
        extent_y_end = 0.25
    else:
        my_colors[:, 3] = np.linspace(0, 1, 256)
        extent_y_start = 0.75
        extent_y_end = 1.0

    custom_cmap = mcolors.ListedColormap(my_colors)
    
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    y_range = ylim[1] - ylim[0]
    
    y_bottom = ylim[0] + y_range * extent_y_start
    y_top = ylim[0] + y_range * extent_y_end
    
    ax.imshow(gradient, extent=[xlim[0], xlim[1], y_bottom, y_top], 
              aspect='auto', cmap=custom_cmap, zorder=zorder, origin='lower')

def parse_color_config(config):
    """
    Parse a color configuration from the theme.
    Returns (is_gradient, value)
    value is either a hex string or a dict/list for gradient.
    """
    if isinstance(config, list):
        # Assume simple list is a vertical gradient
        return True, {"type": "gradient", "colors": config, "direction": "vertical"}
    if isinstance(config, dict) and config.get('type') == 'gradient':
        return True, config
    return False, config

def create_gradient_array(width, height, colors, direction='vertical'):
    """
    Create a gradient RGBA array.
    """
    cmap = mcolors.LinearSegmentedColormap.from_list('feature_gradient', colors)
    
    if direction == 'vertical':
        gradient = np.linspace(0, 1, height).reshape(-1, 1)
        gradient = np.tile(gradient, (1, width))
    else:
        gradient = np.linspace(0, 1, width).reshape(1, -1)
        gradient = np.tile(gradient, (height, 1))
        
    return cmap(gradient)

def geoms_to_path(geoms):
    """
    Convert a GeoSeries of Polygons/MultiPolygons to a single Matplotlib Path.
    """
    codes = []
    verts = []
    for geom in geoms:
        if geom is None or geom.is_empty:
            continue
        
        # Handle single Polygon
        if geom.geom_type == 'Polygon':
            gs = [geom]
        # Handle MultiPolygon
        elif geom.geom_type == 'MultiPolygon':
            gs = geom.geoms
        else:
            continue
            
        for p in gs:
            # Exterior ring
            ext_coords = list(p.exterior.coords)
            if ext_coords:
                verts.extend(ext_coords)
                # Structure: MOVETO, LINETO..., CLOSEPOLY
                # We use the full coords list (including repeated end), but mark last as CLOSEPOLY
                c = [Path.MOVETO] + [Path.LINETO] * (len(ext_coords) - 2) + [Path.CLOSEPOLY]
                codes.extend(c)
            
            # Interior rings (holes)
            for interior in p.interiors:
                int_coords = list(interior.coords)
                if int_coords:
                    verts.extend(int_coords)
                    c = [Path.MOVETO] + [Path.LINETO] * (len(int_coords) - 2) + [Path.CLOSEPOLY]
                    codes.extend(c)
    
    if not verts:
        return None
        
    return Path(verts, codes)

def plot_feature(ax, gdf, theme_key, fallback_color, zorder, alpha=1.0):
    """
    Plot a feature (GeoDataFrame) with either solid color or gradient.
    theme_key: key in THEME dict to look up (e.g., 'water')
    """
    if gdf is None or gdf.empty:
        return

    config = THEME.get(theme_key, fallback_color)
    is_gradient, params = parse_color_config(config)
    
    if not is_gradient:
        # Solid Color
        gdf.plot(ax=ax, facecolor=params, edgecolor='none', alpha=alpha, zorder=zorder)
    else:
        # Gradient Fill
        path = geoms_to_path(gdf.geometry)
        if path is None:
            return
            
        # Create a PathPatch (invisible) for clipping
        patch = PathPatch(path, facecolor='none', edgecolor='none', zorder=zorder)
        ax.add_patch(patch)
        
        # Get gradient params
        colors = params.get('colors', ['#000000', '#FFFFFF'])
        direction = params.get('direction', 'vertical')
        
        # Create gradient image
        # Resolution 512x512 is usually enough for background textures
        grad_img = create_gradient_array(512, 512, colors, direction)
        
        # Determine extent from the axes
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        
        im = ax.imshow(grad_img, extent=[xlim[0], xlim[1], ylim[0], ylim[1]], 
                       origin='lower', aspect='auto', zorder=zorder, alpha=alpha)
        im.set_clip_path(patch)




# Global cache for colormaps to optimize performance
CMAP_CACHE = {}

def get_cached_cmap(colors):
    if isinstance(colors, list):
        colors = tuple(colors)
    if colors not in CMAP_CACHE:
         CMAP_CACHE[colors] = mcolors.LinearSegmentedColormap.from_list(f'cmap_{hash(colors)}', colors)
    return CMAP_CACHE[colors]

def get_edge_colors_by_type(G, bounds=None):
    """
    Assigns colors to edges based on road type hierarchy.
    Supports gradient colors for road types.
    """
    edge_colors = []
    
    # Pre-calculate bounds if needed for gradients
    if bounds is None:
        # crude bounds calculation from nodes
        try:
            x_vals = [d['x'] for n, d in G.nodes(data=True)]
            y_vals = [d['y'] for n, d in G.nodes(data=True)]
            if x_vals and y_vals:
                minx, maxx = min(x_vals), max(x_vals)
                miny, maxy = min(y_vals), max(y_vals)
                bounds = (minx, miny, maxx, maxy)
            else:
                bounds = (0, 0, 1, 1)
        except:
             bounds = (0, 0, 1, 1)

    minx, miny, maxx, maxy = bounds
    width = maxx - minx or 1.0
    height = maxy - miny or 1.0
    
    for u, v, data in G.edges(data=True):
        highway = data.get('highway', 'unclassified')
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'
            
        # Determine strict key
        if highway in ['motorway', 'motorway_link']:
            key = 'road_motorway'
        elif highway in ['trunk', 'trunk_link', 'primary', 'primary_link']:
            key = 'road_primary'
        elif highway in ['secondary', 'secondary_link']:
            key = 'road_secondary'
        elif highway in ['tertiary', 'tertiary_link']:
            key = 'road_tertiary'
        elif highway in ['residential', 'living_street', 'unclassified']:
            key = 'road_residential'
        else:
            key = 'road_default'
            
        config = THEME.get(key, '#3A3A3A')
        is_gradient, params = parse_color_config(config)
        
        if not is_gradient:
            color = params
        else:
            # Calculate edge midpoint position for gradient sampling
            try:
                u_node = G.nodes[u]
                v_node = G.nodes[v]
                mid_x = (u_node['x'] + v_node['x']) / 2
                mid_y = (u_node['y'] + v_node['y']) / 2
                
                direction = params.get('direction', 'vertical')
                if direction == 'vertical':
                    pos = (mid_y - miny) / height
                else:
                    pos = (mid_x - minx) / width
                
                # Clamp position
                pos = max(0.0, min(1.0, pos))
                
                # Sample color from cached colormap
                colors = params.get('colors', ['#000000', '#FFFFFF'])
                cmap = get_cached_cmap(colors)
                color = cmap(pos)
                
            except Exception:
                # Fallback on error
                color = '#000000'

        edge_colors.append(mcolors.to_rgba(color))
            
    return edge_colors

def get_edge_widths_by_type(G):
    """
    Assigns line widths to edges based on road type.
    Major roads get thicker lines.
    """
    edge_widths = []
    
    for u, v, data in G.edges(data=True):
        highway = data.get('highway', 'unclassified')
        
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'
        
        # Assign width based on road importance
        if highway in ['motorway', 'motorway_link']:
            width = 1.2
        elif highway in ['trunk', 'trunk_link', 'primary', 'primary_link']:
            width = 1.0
        elif highway in ['secondary', 'secondary_link']:
            width = 0.8
        elif highway in ['tertiary', 'tertiary_link']:
            width = 0.6
        else:
            width = 0.4
        
        edge_widths.append(width)
    
    return edge_widths

def get_coordinates(city, country):
    """
    Fetches coordinates for a given city and country using geopy.
    Includes rate limiting to be respectful to the geocoding service.
    """
    print("Looking up coordinates...")
    geolocator = Nominatim(user_agent="city_map_poster")
    
    # Add a small delay to respect Nominatim's usage policy
    time.sleep(1)
    
    # Use longer timeout to handle slow network conditions
    location = geolocator.geocode(f"{city}, {country}", timeout=10)
    
    if location:
        print(f"✓ Found: {location.address}")
        print(f"✓ Coordinates: {location.latitude}, {location.longitude}")
        return (location.latitude, location.longitude)
    else:
        raise ValueError(f"Could not find coordinates for {city}, {country}")

def get_stadium_color():
    """
    Returns the color for stadiums from the theme.
    """
    return THEME.get('stadiums', '#E8D5B7')

def get_enabled_features(theme):
    """
    Detect which features are enabled in the theme.
    Returns a dict of feature names mapped to boolean enabled status.
    """
    feature_keys = {
        'water': 'water',
        'parks': 'parks', 
        'stadiums': 'stadiums',
        'railway': 'railway',
        'forest': 'forest',
        'beach': 'beach',
        'coastline': 'coastline',
        'education': 'education',
        'worship': 'worship',
        'airport': 'airport'
    }
    
    enabled = {}
    for feature_name, theme_key in feature_keys.items():
        enabled[feature_name] = theme_key in theme
    
    return enabled

def get_cache_key(point, dist, network_type, enabled_features):
    """
    Generate a unique cache key based on location, distance, network type, and enabled features.
    """
    lat, lon = point
    # Sort enabled features for consistent hashing
    features_str = '_'.join(sorted([k for k, v in enabled_features.items() if v]))
    key_string = f"{lat:.6f}_{lon:.6f}_{dist}_{network_type}_{features_str}"
    return hashlib.md5(key_string.encode()).hexdigest()

def save_to_cache(cache_key, data):
    """
    Save fetched OSM data to cache directory.
    """
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"✓ Saved to cache: {cache_key[:8]}...")
    except Exception as e:
        print(f"⚠ Could not save cache: {e}")

def load_from_cache(cache_key):
    """
    Load OSM data from cache if it exists.
    Returns None if cache miss.
    """
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
            print(f"✓ Loaded from cache: {cache_key[:8]}...")
            return data
        except Exception as e:
            print(f"⚠ Cache corrupted, will re-download: {e}")
            return None
    return None

def create_poster(city, country, point, dist, output_file, use_cache=True, network_type='drive'):
    print(f"\nGenerating map for {city}, {country}...")
    
    # Detect which features are enabled in the current theme
    enabled_features = get_enabled_features(THEME)
    enabled_count = sum(enabled_features.values())
    
    # Show which features will be fetched
    enabled_list = [k for k, v in enabled_features.items() if v]
    if enabled_list:
        print(f"Theme uses {enabled_count} features: {', '.join(enabled_list)}")
    
    # Generate cache key
    cache_key = get_cache_key(point, dist, network_type, enabled_features)
    
    # Try to load from cache
    cached_data = None
    if use_cache:
        cached_data = load_from_cache(cache_key)
    
    if cached_data is not None:
        # Unpack cached data
        G, water, parks, stadiums, railways, forests, beaches, coastlines, education, worship, airports = cached_data
        print("✓ Using cached map data!")
    else:
        # Progress bar for data fetching (1 for streets + enabled features)
        total_steps = 1 + enabled_count
        print("Downloading fresh map data...")
        
        # Initialize all features as None
        water = parks = stadiums = railways = forests = beaches = coastlines = education = worship = airports = None
        
        with tqdm(total=total_steps, desc="Fetching map data", unit="step", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}') as pbar:
            # 1. Fetch Street Network (always needed)
            pbar.set_description("Downloading street network")
            G = ox.graph_from_point(point, dist=dist, dist_type='bbox', network_type=network_type)
            pbar.update(1)
            time.sleep(0.5)  # Rate limit between requests
            
            # 2. Fetch Water Features (conditional)
            if enabled_features['water']:
                pbar.set_description("Downloading water features")
                try:
                    water = ox.features_from_point(point, tags={'natural': 'water', 'waterway': 'riverbank'}, dist=dist)
                except:
                    water = None
                pbar.update(1)
                time.sleep(0.3)
            
            # 3. Fetch Parks (conditional)
            if enabled_features['parks']:
                pbar.set_description("Downloading parks/green spaces")
                try:
                    parks = ox.features_from_point(point, tags={'leisure': 'park', 'landuse': 'grass'}, dist=dist)
                except:
                    parks = None
                pbar.update(1)
                time.sleep(0.3)
            
            # 4. Fetch Stadiums (conditional)
            if enabled_features['stadiums']:
                pbar.set_description("Downloading stadiums")
                try:
                    stadiums = ox.features_from_point(point, tags={'leisure': 'stadium', 'building': 'stadium'}, dist=dist)
                except:
                    stadiums = None
                pbar.update(1)
                time.sleep(0.3)
            
            # 5. Fetch Railways (conditional)
            if enabled_features['railway']:
                pbar.set_description("Downloading railways/transit")
                try:
                    railways = ox.features_from_point(point, tags={'railway': ['rail', 'subway', 'tram', 'light_rail']}, dist=dist)
                except:
                    railways = None
                pbar.update(1)
                time.sleep(0.3)
            
            # 6. Fetch Forests (conditional)
            if enabled_features['forest']:
                pbar.set_description("Downloading forests/woods")
                try:
                    forests = ox.features_from_point(point, tags={'natural': 'wood', 'landuse': 'forest'}, dist=dist)
                except:
                    forests = None
                pbar.update(1)
                time.sleep(0.3)
            
            # 7. Fetch Beaches (conditional)
            if enabled_features['beach']:
                pbar.set_description("Downloading beaches")
                try:
                    beaches = ox.features_from_point(point, tags={'natural': 'beach'}, dist=dist)
                except:
                    beaches = None
                pbar.update(1)
                time.sleep(0.3)
            
            # 8. Fetch Coastlines (conditional)
            if enabled_features['coastline']:
                pbar.set_description("Downloading coastlines")
                try:
                    coastlines = ox.features_from_point(point, tags={'natural': 'coastline'}, dist=dist)
                except:
                    coastlines = None
                pbar.update(1)
                time.sleep(0.3)
            
            # 9. Fetch Education (conditional)
            if enabled_features['education']:
                pbar.set_description("Downloading education facilities")
                try:
                    education = ox.features_from_point(point, tags={'amenity': ['university', 'college', 'school']}, dist=dist)
                except:
                    education = None
                pbar.update(1)
                time.sleep(0.3)
            
            # 10. Fetch Places of Worship (conditional)
            if enabled_features['worship']:
                pbar.set_description("Downloading places of worship")
                try:
                    worship = ox.features_from_point(point, tags={'amenity': 'place_of_worship'}, dist=dist)
                except:
                    worship = None
                pbar.update(1)
                time.sleep(0.3)
            
            # 11. Fetch Airports (conditional)
            if enabled_features['airport']:
                pbar.set_description("Downloading airports")
                try:
                    airports = ox.features_from_point(point, tags={'aeroway': ['aerodrome', 'runway', 'apron']}, dist=dist)
                except:
                    airports = None
                pbar.update(1)
        
        print("✓ All data downloaded successfully!")
        
        # Save to cache
        if use_cache:
            cache_data = (G, water, parks, stadiums, railways, forests, beaches, coastlines, education, worship, airports)
            save_to_cache(cache_key, cache_data)
    
    # 2. Setup Plot
    print("Rendering map...")
    fig, ax = plt.subplots(figsize=(12, 16), facecolor=THEME['bg'])
    ax.set_facecolor(THEME['bg'])
    ax.set_position([0, 0, 1, 1])
    
    # Calculate and set bounds based on street network to ensure consistent gradient rendering
    node_points = [(data['x'], data['y']) for node, data in G.nodes(data=True)]
    bounds = None
    if node_points:
        xs, ys = zip(*node_points)
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        bounds = (minx, miny, maxx, maxy)

    
    # 3. Plot Layers
    
    def filter_geom(gdf, geom_types):
        """Filter GeoDataFrame to only retain specified geometry types."""
        if gdf is None or gdf.empty:
            return gdf
        return gdf[gdf.geometry.type.isin(geom_types)]

    # Filter area features to only show actual areas (Polygons/MultiPolygons)
    # This prevents single nodes (Points) like water fountains or small park nodes from appearing as dots
    area_features = ['Polygon', 'MultiPolygon']
    water = filter_geom(water, area_features)
    parks = filter_geom(parks, area_features)
    forests = filter_geom(forests, area_features)
    beaches = filter_geom(beaches, area_features)
    education = filter_geom(education, area_features)
    airports = filter_geom(airports, area_features)
    
    # Layer 0: Base natural features
    if coastlines is not None and not coastlines.empty:
        coastlines.plot(ax=ax, edgecolor=THEME.get('coastline', '#1E90FF'), linewidth=1.25, facecolor='none', zorder=0.5)
    
    # Layer 1: Area fills - natural features
    plot_feature(ax, forests, 'forest', '#228B22', zorder=1)
    plot_feature(ax, beaches, 'beach', '#F4A460', zorder=1.2)
    # Using safe get for water default to match previous behavior
    plot_feature(ax, water, 'water', '#C0C0C0', zorder=1.5)
    
    # Layer 2: Area fills - urban features
    plot_feature(ax, parks, 'parks', '#F0F0F0', zorder=2)
    plot_feature(ax, airports, 'airport', '#D3D3D3', zorder=2.2, alpha=0.6)
    plot_feature(ax, education, 'education', '#FFD700', zorder=2.3, alpha=0.5)
    
    # Layer 3: Point features
    if stadiums is not None and not stadiums.empty:
        # Plot as circles (centroids) instead of shapes
        stadiums.geometry.centroid.plot(ax=ax, color=THEME.get('stadiums', '#E8D5B7'), markersize=80, zorder=3)
    if worship is not None and not worship.empty:
        # Plot places of worship as small points
        worship.geometry.centroid.plot(ax=ax, color=THEME.get('worship', '#8B4513'), markersize=30, zorder=3)
    
    # Layer 4: Railways (before roads)
    if railways is not None and not railways.empty:
        railways.plot(ax=ax, edgecolor=THEME.get('railway', '#A9A9A9'), linewidth=0.8, facecolor='none', zorder=3.5)
    
    # Layer 2: Roads with hierarchy coloring
    print("Applying road hierarchy colors...")
    edge_colors = get_edge_colors_by_type(G, bounds)
    edge_widths = get_edge_widths_by_type(G)
    
    ox.plot_graph(
        G, ax=ax, bgcolor=THEME['bg'],
        node_size=0,
        node_color=THEME['bg'],
        node_alpha=0,
        edge_color=edge_colors,
        edge_linewidth=edge_widths,
        show=False, close=False
    )
    
    # Layer 3: Gradients (Top and Bottom)
    create_gradient_fade(ax, THEME['gradient_color'], location='bottom', zorder=10)
    create_gradient_fade(ax, THEME['gradient_color'], location='top', zorder=10)
    
    # 4. Typography using Roboto font
    if FONTS:
        font_main = FontProperties(fname=FONTS['bold'], size=60)
        font_top = FontProperties(fname=FONTS['bold'], size=40)
        font_sub = FontProperties(fname=FONTS['light'], size=22)
        font_coords = FontProperties(fname=FONTS['regular'], size=14)
    else:
        # Fallback to system fonts
        font_main = FontProperties(family='monospace', weight='bold', size=60)
        font_top = FontProperties(family='monospace', weight='bold', size=40)
        font_sub = FontProperties(family='monospace', weight='normal', size=22)
        font_coords = FontProperties(family='monospace', size=14)
    
    spaced_city = "  ".join(list(city.upper()))

    # --- BOTTOM TEXT ---
    ax.text(0.5, 0.14, spaced_city, transform=ax.transAxes,
            color=THEME['text'], ha='center', fontproperties=font_main, zorder=11)
    
    ax.text(0.5, 0.10, country.upper(), transform=ax.transAxes,
            color=THEME['text'], ha='center', fontproperties=font_sub, zorder=11)
    
    lat, lon = point
    
    # Format coordinates with spaces around / and bold cardinal directions
    lat_dir = 'N' if lat >= 0 else 'S'
    lon_dir = 'E' if lon >= 0 else 'W'
    
    # Create coordinate string with spaces around /
    coords_base = f"{abs(lat):.4f}° {lat_dir}  /  {abs(lon):.4f}° {lon_dir}"
    
    # For bold cardinal directions, we'll use matplotlib's text with different weights
    # Create the full string but we'll render it with formatting
    if FONTS:
        font_coords_bold = FontProperties(fname=FONTS['bold'], size=14)
    else:
        font_coords_bold = FontProperties(family='monospace', weight='bold', size=14)
    
    # Split and render with bold cardinal directions
    # Using a single text element with the formatted string
    lat_str = f"{abs(lat):.4f}°"
    lon_str = f"{abs(lon):.4f}°"
    
    # Build formatted coordinate string with bold markers
    # We'll use matplotlib's text formatting: $\mathbf{X}$ for bold
    coords_formatted = f"{lat_str} $\\mathbf{{{lat_dir}}}$  /  {lon_str} $\\mathbf{{{lon_dir}}}$"
    
    ax.text(0.5, 0.07, coords_formatted, transform=ax.transAxes,
            color=THEME['text'], alpha=0.7, ha='center', fontproperties=font_coords, zorder=11)
    
    ax.plot([0.4, 0.6], [0.125, 0.125], transform=ax.transAxes, 
            color=THEME['text'], linewidth=0.5, zorder=11)

    # # --- ATTRIBUTION (bottom right) ---
    # if FONTS:
    #     font_attr = FontProperties(fname=FONTS['light'], size=8)
    # else:
    #     font_attr = FontProperties(family='monospace', size=8)
    
    # ax.text(0.98, 0.02, "© OpenStreetMap contributors", transform=ax.transAxes,
    #         color=THEME['text'], alpha=0.5, ha='right', va='bottom', 
    #         fontproperties=font_attr, zorder=11)

    # 5. Save
    print(f"Saving to {output_file}...")
    plt.savefig(output_file, dpi=300, facecolor=THEME['bg'])
    plt.close()
    print(f"✓ Done! Poster saved as {output_file}")

def print_examples():
    """Print usage examples."""
    print("""
City Map Poster Generator
=========================

Usage:
  python create_map_poster.py --city <city> --country <country> [options]

Examples:
  # Iconic grid patterns
  python create_map_poster.py -c "New York" -C "USA" -t noir -d 12000           # Manhattan grid
  python create_map_poster.py -c "Barcelona" -C "Spain" -t warm_beige -d 8000   # Eixample district grid
  
  # Waterfront & canals
  python create_map_poster.py -c "Venice" -C "Italy" -t blueprint -d 4000       # Canal network
  python create_map_poster.py -c "Amsterdam" -C "Netherlands" -t ocean -d 6000  # Concentric canals
  python create_map_poster.py -c "Dubai" -C "UAE" -t midnight_blue -d 15000     # Palm & coastline
  
  # Radial patterns
  python create_map_poster.py -c "Paris" -C "France" -t pastel_dream -d 10000   # Haussmann boulevards
  python create_map_poster.py -c "Moscow" -C "Russia" -t noir -d 12000          # Ring roads
  
  # Organic old cities
  python create_map_poster.py -c "Tokyo" -C "Japan" -t japanese_ink -d 15000    # Dense organic streets
  python create_map_poster.py -c "Marrakech" -C "Morocco" -t terracotta -d 5000 # Medina maze
  python create_map_poster.py -c "Rome" -C "Italy" -t warm_beige -d 8000        # Ancient street layout
  
  # Coastal cities
  python create_map_poster.py -c "San Francisco" -C "USA" -t sunset -d 10000    # Peninsula grid
  python create_map_poster.py -c "Sydney" -C "Australia" -t ocean -d 12000      # Harbor city
  python create_map_poster.py -c "Mumbai" -C "India" -t contrast_zones -d 18000 # Coastal peninsula
  
  # River cities
  python create_map_poster.py -c "London" -C "UK" -t noir -d 15000              # Thames curves
  python create_map_poster.py -c "Budapest" -C "Hungary" -t copper_patina -d 8000  # Danube split
  
  # List themes
  python create_map_poster.py --list-themes

Options:
  --city, -c        City name (required)
  --country, -C     Country name (required)
  --theme, -t       Theme name (default: feature_based)
  --distance, -d    Map radius in meters (default: 29000)
  --list-themes     List all available themes

Distance guide:
  4000-6000m   Small/dense cities (Venice, Amsterdam old center)
  8000-12000m  Medium cities, focused downtown (Paris, Barcelona)
  15000-20000m Large metros, full city view (Tokyo, Mumbai)

Available themes can be found in the 'themes/' directory.
Generated posters are saved to 'posters/' directory.
""")

def list_themes():
    """List all available themes with descriptions."""
    available_themes = get_available_themes()
    if not available_themes:
        print("No themes found in 'themes/' directory.")
        return
    
    print("\nAvailable Themes:")
    print("-" * 60)
    for theme_name in available_themes:
        theme_path = os.path.join(THEMES_DIR, f"{theme_name}.json")
        try:
            with open(theme_path, 'r') as f:
                theme_data = json.load(f)
                display_name = theme_data.get('name', theme_name)
                description = theme_data.get('description', '')
        except:
            display_name = theme_name
            description = ''
        print(f"  {theme_name}")
        print(f"    {display_name}")
        if description:
            print(f"    {description}")
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate beautiful map posters for any city",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_map_poster.py --city "New York" --country "USA"
  python create_map_poster.py --city Tokyo --country Japan --theme midnight_blue
  python create_map_poster.py --city Paris --country France --theme noir --distance 15000
  python create_map_poster.py --list-themes
        """
    )
    
    parser.add_argument('--city', '-c', type=str, help='City name')
    parser.add_argument('--country', '-C', type=str, help='Country name')
    parser.add_argument('--theme', '-t', type=str, default='feature_based', help='Theme name (default: feature_based)')
    parser.add_argument('--distance', '-d', type=int, default=29000, help='Map radius in meters (default: 29000)')
    parser.add_argument('--network-type', '-n', type=str, default='drive', 
                        choices=['drive', 'all', 'walk', 'bike'],
                        help='Street network type: drive (faster), all (complete), walk, bike (default: drive)')
    parser.add_argument('--no-cache', action='store_true', help='Disable caching, always download fresh data')
    parser.add_argument('--list-themes', action='store_true', help='List all available themes')
    
    args = parser.parse_args()
    
    # If no arguments provided, show examples
    if len(os.sys.argv) == 1:
        print_examples()
        os.sys.exit(0)
    
    # List themes if requested
    if args.list_themes:
        list_themes()
        os.sys.exit(0)
    
    # Validate required arguments
    if not args.city or not args.country:
        print("Error: --city and --country are required.\n")
        print_examples()
        os.sys.exit(1)
    
    # Validate theme exists
    available_themes = get_available_themes()
    if args.theme not in available_themes:
        print(f"Error: Theme '{args.theme}' not found.")
        print(f"Available themes: {', '.join(available_themes)}")
        os.sys.exit(1)
    
    print("=" * 50)
    print("City Map Poster Generator")
    print("=" * 50)
    
    # Load theme
    THEME = load_theme(args.theme)
    
    # Get coordinates and generate poster
    try:
        coords = get_coordinates(args.city, args.country)
        output_file = generate_output_filename(args.city, args.theme)
        use_cache = not args.no_cache
        create_poster(args.city, args.country, coords, args.distance, output_file, 
                     use_cache=use_cache, network_type=args.network_type)
        
        print("\n" + "=" * 50)
        print("✓ Poster generation complete!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        os.sys.exit(1)
        