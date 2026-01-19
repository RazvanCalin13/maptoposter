# City Map Poster Generator

Generate beautiful, minimalist map posters for any city in the world.

<img src="posters/singapore_neon_cyberpunk_20260108_184503.png" width="250">
<img src="posters/dubai_midnight_blue_20260108_174920.png" width="250">

## Examples


| Country      | City           | Theme           | Poster |
|:------------:|:--------------:|:---------------:|:------:|
| USA          | San Francisco  | sunset          | <img src="posters/san_francisco_sunset_20260108_184122.png" width="250"> |
| Spain        | Barcelona      | warm_beige      | <img src="posters/barcelona_warm_beige_20260108_172924.png" width="250"> |
| Italy        | Venice         | blueprint       | <img src="posters/venice_blueprint_20260108_165527.png" width="250"> |
| Japan        | Tokyo          | japanese_ink    | <img src="posters/tokyo_japanese_ink_20260108_165830.png" width="250"> |
| India        | Mumbai         | contrast_zones  | <img src="posters/mumbai_contrast_zones_20260108_170325.png" width="250"> |
| Morocco      | Marrakech      | terracotta      | <img src="posters/marrakech_terracotta_20260108_180821.png" width="250"> |
| Singapore    | Singapore      | neon_cyberpunk  | <img src="posters/singapore_neon_cyberpunk_20260108_184503.png" width="250"> |
| Australia    | Melbourne      | forest          | <img src="posters/melbourne_forest_20260108_181459.png" width="250"> |
| UAE          | Dubai          | midnight_blue   | <img src="posters/dubai_midnight_blue_20260108_174920.png" width="250"> |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python create_map_poster.py --city <city> --country <country> [options]
```

### Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--city` | `-c` | City name | required |
| `--country` | `-C` | Country name | required |
| `--theme` | `-t` | Theme name | feature_based |
| `--distance` | `-d` | Map radius in meters | 29000 |
| `--network-type` | `-n` | Street network: `drive` (faster), `all`, `walk`, `bike` | drive |
| `--no-cache` | | Disable caching, always download fresh | (caching enabled) |
| `--list-themes` | | List all available themes | |

### Examples

```bash
# Iconic grid patterns
python create_map_poster.py -c "New York" -C "USA" -t noir -d 12000           # Manhattan grid
python create_map_poster.py -c "Barcelona" -C "Spain" -t warm_beige -d 8000   # Eixample district

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
python create_map_poster.py -c "Rome" -C "Italy" -t warm_beige -d 8000        # Ancient layout

# Coastal cities
python create_map_poster.py -c "San Francisco" -C "USA" -t sunset -d 10000    # Peninsula grid
python create_map_poster.py -c "Sydney" -C "Australia" -t ocean -d 12000      # Harbor city
python create_map_poster.py -c "Mumbai" -C "India" -t contrast_zones -d 18000 # Coastal peninsula

# River cities
python create_map_poster.py -c "London" -C "UK" -t noir -d 15000              # Thames curves
python create_map_poster.py -c "Budapest" -C "Hungary" -t copper_patina -d 8000  # Danube split

# List available themes
python create_map_poster.py --list-themes
```

### Distance Guide

| Distance | Best for |
|----------|----------|
| 4000-6000m | Small/dense cities (Venice, Amsterdam center) |
| 8000-12000m | Medium cities, focused downtown (Paris, Barcelona) |
| 15000-20000m | Large metros, full city view (Tokyo, Mumbai) |

## Themes

17 themes available in `themes/` directory:

| Theme | Style |
|-------|-------|
| `feature_based` | Classic black & white with road hierarchy |
| `gradient_roads` | Smooth gradient shading |
| `contrast_zones` | High contrast urban density |
| `noir` | Pure black background, white roads |
| `midnight_blue` | Navy background with gold roads |
| `blueprint` | Architectural blueprint aesthetic |
| `neon_cyberpunk` | Dark with electric pink/cyan |
| `warm_beige` | Vintage sepia tones |
| `pastel_dream` | Soft muted pastels |
| `japanese_ink` | Minimalist ink wash style |
| `forest` | Deep greens and sage |
| `ocean` | Blues and teals for coastal cities |
| `terracotta` | Mediterranean warmth |
| `sunset` | Warm oranges and pinks |
| `autumn` | Seasonal burnt oranges and reds |
| `copper_patina` | Oxidized copper aesthetic |
| `monochrome_blue` | Single blue color family |

## Output

Posters are saved to `posters/` directory with format:
```
{city}_{theme}_{YYYYMMDD_HHMMSS}.png
```

## Performance

### Smart Feature Detection 🧠

The script **automatically detects** which map features are used in your theme and **only downloads those**!

**Example - Noir theme** (minimal, only has water/parks/beach):
```bash
python create_map_poster.py -c "Amsterdam" -C "Netherlands" -t noir
# ✓ Theme uses 3 features: water, parks, beach
# ✓ Downloads 4 items instead of 11 (3x faster!)
```

**Example - Full-featured theme** (has all 10 features):
```bash
python create_map_poster.py -c "Tokyo" -C "Japan" -t custom_full
# ✓ Theme uses 10 features: water, parks, stadiums, railway, forest, beach...
# ✓ Downloads all 11 items (slower but complete)
```

**How it works:**
- Checks theme JSON for feature color keys
- Only fetches features that are defined
- Automatically updates progress bar and cache keys
- No configuration needed - it just works!

### Caching System ⚡

The script automatically caches downloaded OpenStreetMap data to speed up subsequent renders of the same location.

**First run** (Barcelona, 4km radius):
- Downloads all map data: ~30-60 seconds
- Saves to `cache/` directory

**Second run** (same city/distance):
- Loads from cache: **~2 seconds** (15-30x faster!)
- Cache key based on coordinates, distance, network type, AND enabled features

**Clear cache:**
```bash
rm -rf cache/      # Clear all cached data
```

**Disable caching:**
```bash
python create_map_poster.py -c "Paris" -C "France" --no-cache
```

### Network Types

The `--network-type` flag controls which roads are downloaded:

| Type | Speed | Use Case |
|------|-------|----------|
| `drive` (default) | ⚡ Fastest | Main roads, highways - clean minimal look |
| `all` | 🐌 Slowest | Every path/trail - ultra-detailed |
| `walk` | 🚶 Medium | Pedestrian paths included |
| `bike` | 🚴 Medium | Bike lanes and paths |

**Example:**
```bash
# Fast, clean render (default)
python create_map_poster.py -c "Tokyo" -C "Japan" -t noir

# Detailed render with all paths
python create_map_poster.py -c "Tokyo" -C "Japan" -t noir -n all
```

## Adding Custom Themes

Create a JSON file in `themes/` directory:

```json
{
  "name": "My Theme",
  "description": "Description of the theme",
  "bg": "#FFFFFF",
  "text": "#000000",
  "gradient_color": "#FFFFFF",
  "water": "#C0C0C0",
  "parks": "#F0F0F0",
  "stadiums": "#ff0000ff",
  "railway": "#808080",
  "forest": "#228B22",
  "beach": "#F4A460",
  "coastline": "#1E90FF",
  "education": "#FFD700",
  "worship": "#8B4513",
  "airport": "#D3D3D3",
  "road_motorway": "#0A0A0A",
  "road_primary": "#1A1A1A",
  "road_secondary": "#2A2A2A",
  "road_tertiary": "#3A3A3A",
  "road_residential": "#4A4A4A",
  "road_default": "#3A3A3A"
}
```

### Available Theme Attributes

| Attribute | Type | Description | Default Fallback |
|-----------|------|-------------|------------------|
| `bg` | Color | Background color | `#FFFFFF` |
| `text` | Color | City name, country, coordinates text | `#000000` |
| `gradient_color` | Color | Top/bottom fade gradient | `#FFFFFF` |
| `water` | Color | Rivers, lakes, water bodies | `#C0C0C0` |
| `parks` | Color | Parks, green spaces, grass areas | `#F0F0F0` |
| `stadiums` | Color | Stadium markers (rendered as circles) | `#E8D5B7` |
| `railway` | Color | Rail, subway, tram, light rail lines | `#A9A9A9` |
| `forest` | Color | Woods, forests, tree coverage | `#228B22` |
| `beach` | Color | Beach areas | `#F4A460` |
| `coastline` | Color | Ocean/sea borders | `#1E90FF` |
| `education` | Color | Universities, colleges, schools | `#FFD700` |
| `worship` | Color | Places of worship (rendered as small circles) | `#8B4513` |
| `airport` | Color | Airports, runways, aprons | `#D3D3D3` |
| `road_motorway` | Color | Highways, motorways | `#0A0A0A` |
| `road_primary` | Color | Primary/trunk roads | `#1A1A1A` |
| `road_secondary` | Color | Secondary roads | `#2A2A2A` |
| `road_tertiary` | Color | Tertiary roads | `#3A3A3A` |
| `road_residential` | Color | Residential streets | `#4A4A4A` |
| `road_default` | Color | Other roads | `#3A3A3A` |

### OpenStreetMap Feature Tags

The script fetches data from OpenStreetMap using the following tags:

| Feature | OSM Tags | Rendering |
|---------|----------|-----------|
| **Streets** | `network_type='all'` | Lines with hierarchy-based width/color |
| **Water** | `natural=water`, `waterway=riverbank` | Filled polygons |
| **Parks** | `leisure=park`, `landuse=grass` | Filled polygons |
| **Stadiums** | `leisure=stadium`, `building=stadium` | Circle markers at centroid |
| **Railways** | `railway=[rail, subway, tram, light_rail]` | Lines |
| **Forests** | `natural=wood`, `landuse=forest` | Filled polygons |
| **Beaches** | `natural=beach` | Filled polygons |
| **Coastlines** | `natural=coastline` | Line borders |
| **Education** | `amenity=[university, college, school]` | Filled polygons (semi-transparent) |
| **Places of Worship** | `amenity=place_of_worship` | Small circle markers at centroid |
| **Airports** | `aeroway=[aerodrome, runway, apron]` | Filled polygons (semi-transparent) |


## Project Structure

```
map_poster/
├── create_map_poster.py          # Main script
├── themes/               # Theme JSON files
├── fonts/                # Roboto font files
├── posters/              # Generated posters
└── README.md
```

## Hacker's Guide

Quick reference for contributors who want to extend or modify the script.

### Architecture Overview

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   CLI Parser    │────▶│  Geocoding   │────▶│  Data Fetching  │
│   (argparse)    │     │  (Nominatim) │     │    (OSMnx)      │
└─────────────────┘     └──────────────┘     └─────────────────┘
                                                     │
                        ┌──────────────┐             ▼
                        │    Output    │◀────┌─────────────────┐
                        │  (matplotlib)│     │   Rendering     │
                        └──────────────┘     │  (matplotlib)   │
                                             └─────────────────┘
```

### Key Functions

| Function | Purpose | Modify when... |
|----------|---------|----------------|
| `get_coordinates()` | City → lat/lon via Nominatim | Switching geocoding provider |
| `create_poster()` | Main rendering pipeline | Adding new map layers |
| `get_edge_colors_by_type()` | Road color by OSM highway tag | Changing road styling |
| `get_edge_widths_by_type()` | Road width by importance | Adjusting line weights |
| `create_gradient_fade()` | Top/bottom fade effect | Modifying gradient overlay |
| `load_theme()` | JSON theme → dict | Adding new theme properties |

### Rendering Layers (z-order)

```
z=11   Text labels (city, country, coords)
z=10   Gradient fades (top & bottom)
z=4    Roads (via ox.plot_graph)
z=3.5  Railways (rail, subway, tram)
z=3    Point features (stadiums, places of worship)
z=2.3  Education facilities (semi-transparent)
z=2.2  Airports (semi-transparent)
z=2    Parks (green polygons)
z=1.5  Water (blue polygons)
z=1.2  Beaches
z=1    Forests
z=0.5  Coastlines
z=0    Background color
```

### OSM Highway Types → Road Hierarchy

```python
# In get_edge_colors_by_type() and get_edge_widths_by_type()
motorway, motorway_link     → Thickest (1.2), darkest
trunk, primary              → Thick (1.0)
secondary                   → Medium (0.8)
tertiary                    → Thin (0.6)
residential, living_street  → Thinnest (0.4), lightest
```

### Adding New Features

**Example: Adding a new map layer (e.g., buildings):**
```python
# 1. In create_poster(), add to the fetching section:
try:
    buildings = ox.features_from_point(point, tags={'building': True}, dist=dist)
except:
    buildings = None

# 2. Then plot in the appropriate layer (choose correct z-order):
if buildings is not None and not buildings.empty:
    buildings.plot(ax=ax, facecolor=THEME.get('building', '#CCCCCC'), 
                   edgecolor='none', alpha=0.3, zorder=1.8)
```

**New theme property:**
1. Add to theme JSON: `"building": "#CCCCCC"`
2. Use in code with fallback: `THEME.get('building', '#CCCCCC')`
3. Document in README attributes table

### Typography Positioning

All text uses `transform=ax.transAxes` (0-1 normalized coordinates):
```
y=0.14  City name (spaced letters)
y=0.125 Decorative line
y=0.10  Country name
y=0.07  Coordinates
y=0.02  Attribution (bottom-right)
```

### Useful OSMnx Patterns

```python
# Get all buildings
buildings = ox.features_from_point(point, tags={'building': True}, dist=dist)

# Get specific amenities
cafes = ox.features_from_point(point, tags={'amenity': 'cafe'}, dist=dist)

# Different network types
G = ox.graph_from_point(point, dist=dist, network_type='drive')  # roads only
G = ox.graph_from_point(point, dist=dist, network_type='bike')   # bike paths
G = ox.graph_from_point(point, dist=dist, network_type='walk')   # pedestrian
```

### Performance Tips

- Large `dist` values (>20km) = slow downloads + memory heavy
- Cache coordinates locally to avoid Nominatim rate limits
- Use `network_type='drive'` instead of `'all'` for faster renders
- Reduce `dpi` from 300 to 150 for quick previews
