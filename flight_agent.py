"""
AI Flight Search Agent - Fixed Hotel Location Search
"""

import os
from datetime import datetime, timedelta
import json
from anthropic import Anthropic
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='.')
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Map airport codes to city names for hotel searches
AIRPORT_TO_CITY = {
    # Europe
    "BCN": "Barcelona, Spain",
    "MAD": "Madrid, Spain",
    "PAR": "Paris, France",
    "ROM": "Rome, Italy",
    "AMS": "Amsterdam, Netherlands",
    "BER": "Berlin, Germany",
    "LIS": "Lisbon, Portugal",
    "DUB": "Dublin, Ireland",
    "VIE": "Vienna, Austria",
    "PRG": "Prague, Czech Republic",
    
    # USA
    "NYC": "New York, USA",
    "LAX": "Los Angeles, USA",
    "MIA": "Miami, USA",
    "SFO": "San Francisco, USA",
    "LAS": "Las Vegas, USA",
    
    # Asia & Middle East
    "DXB": "Dubai, UAE",
    "BKK": "Bangkok, Thailand",
    "SIN": "Singapore",
    "TYO": "Tokyo, Japan",
    "HKG": "Hong Kong",
    
    # UK (in case someone searches from one UK city to another)
    "LHR": "London, UK",
    "LGW": "London, UK",
    "STN": "London, UK",
    "LTN": "London, UK",
    "LCY": "London, UK",
    "MAN": "Manchester, UK",
    "BHX": "Birmingham, UK",
    "EDI": "Edinburgh, UK",
    "GLA": "Glasgow, UK",
    "BRS": "Bristol, UK",
    "NCL": "Newcastle, UK",
    "LPL": "Liverpool, UK"
}

def get_city_name(airport_code):
    """Convert airport code to city name for hotel searches"""
    return AIRPORT_TO_CITY.get(airport_code, airport_code)

class TravelPlanningAgent:
    def __init__(self):
        self.serpapi_key = os.environ.get("SERPAPI_KEY")
        
    def search_flights(self, origin, destination, outbound_date, return_date=None):
        """Search flights with detailed times and prices"""
        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": outbound_date,
            "currency": "GBP",
            "hl": "en",
            "api_key": self.serpapi_key
        }
        
        if return_date:
            params["return_date"] = return_date
            params["type"] = "1"
        
        try:
            response = requests.get("https://serpapi.com/search", params=params, timeout=30)
            return response.json()
        except Exception as e:
            print(f"Flight search error: {e}")
            return {"error": str(e)}
    
    def search_hotels(self, destination_code, check_in, check_out):
        """Search hotels with images and detailed info - using proper city names"""
        # Convert airport code to city name
        city_name = get_city_name(destination_code)
        
        print(f"Searching hotels for: {city_name} (from code: {destination_code})")
        
        params = {
            "engine": "google_hotels",
            "q": city_name,
            "check_in_date": check_in,
            "check_out_date": check_out,
            "currency": "GBP",
            "gl": "uk",
            "hl": "en",
            "api_key": self.serpapi_key
        }
        
        try:
            response = requests.get("https://serpapi.com/search", params=params, timeout=30)
            result = response.json()
            print(f"Hotel API returned {len(result.get('properties', []))} properties")
            return result
        except Exception as e:
            print(f"Hotel search error: {e}")
            return {"error": str(e)}
    
    def search_airbnb(self, destination_code, check_in, check_out):
        """Search Airbnb listings - using proper city names"""
        # Convert airport code to city name
        city_name = get_city_name(destination_code)
        
        print(f"Searching Airbnb for: {city_name} (from code: {destination_code})")
        
        check_in_date = datetime.strptime(check_in, "%Y-%m-%d")
        check_out_date = datetime.strptime(check_out, "%Y-%m-%d")
        nights = (check_out_date - check_in_date).days
        
        params = {
            "engine": "google",
            "q": f"airbnb {city_name}",
            "api_key": self.serpapi_key,
            "num": 10
        }
        
        try:
            response = requests.get("https://serpapi.com/search", params=params, timeout=30)
            results = response.json()
            
            airbnb_listings = []
            if "organic_results" in results:
                for result in results["organic_results"][:8]:
                    if "airbnb" in result.get("link", "").lower():
                        airbnb_listings.append({
                            "name": result.get("title", "Airbnb Listing"),
                            "description": result.get("snippet", ""),
                            "link": result.get("link", "#"),
                            "price_per_night": "50-150",
                            "total_price": f"{nights * 75}",
                            "type": "Entire home/Private room"
                        })
            
            print(f"Found {len(airbnb_listings)} Airbnb listings")
            return airbnb_listings
        except Exception as e:
            print(f"Airbnb search error: {e}")
            return []
    
    def analyze_flexible_dates(self, origin, destination, start_date, return_date, days_range=7):
        """Search flights across flexible dates with detailed flight info"""
        results = []
        base_date = datetime.strptime(start_date, "%Y-%m-%d")
        
        if return_date:
            return_date_obj = datetime.strptime(return_date, "%Y-%m-%d")
        
        for i in range(days_range):
            search_date = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
            search_return = (return_date_obj + timedelta(days=i)).strftime("%Y-%m-%d") if return_date else None
            
            flight_data = self.search_flights(origin, destination, search_date, search_return)
            
            if "best_flights" in flight_data:
                for flight in flight_data.get("best_flights", [])[:3]:
                    flights_info = flight.get("flights", [])
                    
                    outbound_flight = flights_info[0] if flights_info else {}
                    
                    return_flight = None
                    if len(flights_info) > 1:
                        return_flight = flights_info[1]
                    
                    flight_details = {
                        "outbound_date": search_date,
                        "return_date": search_return,
                        "price": flight.get("price"),
                        "total_duration": flight.get("total_duration"),
                        "airline": outbound_flight.get("airline", "Unknown"),
                        "airline_logo": outbound_flight.get("airline_logo", ""),
                        
                        "outbound_departure_time": outbound_flight.get("departure_airport", {}).get("time", ""),
                        "outbound_arrival_time": outbound_flight.get("arrival_airport", {}).get("time", ""),
                        "outbound_departure_airport": outbound_flight.get("departure_airport", {}).get("id", origin),
                        "outbound_arrival_airport": outbound_flight.get("arrival_airport", {}).get("id", destination),
                        "outbound_duration": outbound_flight.get("duration"),
                        
                        "return_departure_time": return_flight.get("departure_airport", {}).get("time", "") if return_flight else "",
                        "return_arrival_time": return_flight.get("arrival_airport", {}).get("time", "") if return_flight else "",
                        "return_duration": return_flight.get("duration") if return_flight else "",
                        
                        "booking_link": f"https://www.google.com/travel/flights?q={origin}+to+{destination}+on+{search_date}",
                        "layovers": outbound_flight.get("layovers", [])
                    }
                    
                    results.append(flight_details)
        
        return results
    
    def create_structured_itinerary(self, destination_code, keywords, budget, duration_days, hotels):
        """Create comprehensive structured itinerary with AI - using proper city names"""
        # Convert airport code to city name for AI context
        city_name = get_city_name(destination_code)
        
        print(f"Creating itinerary for: {city_name}")
        
        hotel_info = ""
        if hotels and "properties" in hotels:
            top_hotels = hotels["properties"][:3]
            hotel_info = "\n\nTop Hotels:\n"
            for hotel in top_hotels:
                hotel_info += f"- {hotel.get('name', 'N/A')}: £{hotel.get('rate_per_night', {}).get('lowest', 'N/A')}/night\n"
        
        prompt = f"""Create a {duration_days}-day itinerary for {city_name}.

CRITICAL: You MUST respond with ONLY valid JSON. No other text before or after.

Required JSON structure:
{{
  "overview": {{
    "destination": "{city_name}",
    "best_time_to_visit": "Best months to visit",
    "getting_around": "How to get around the city",
    "money_saving_tips": ["tip 1", "tip 2", "tip 3"],
    "local_customs": "Important cultural customs"
  }},
  "daily_itinerary": [
    {{
      "day": 1,
      "theme": "Cultural Exploration",
      "morning": {{
        "time": "9:00 AM",
        "activity": "Activity name",
        "description": "Detailed description",
        "cost": 15,
        "duration": "2 hours",
        "location": "Neighborhood name"
      }},
      "afternoon": {{
        "time": "2:00 PM",
        "activity": "Activity name",
        "description": "Detailed description",
        "cost": 25,
        "duration": "3 hours",
        "location": "Neighborhood name"
      }},
      "evening": {{
        "time": "7:00 PM",
        "activity": "Activity name",
        "description": "Detailed description",
        "cost": 35,
        "duration": "2 hours",
        "location": "Neighborhood name"
      }},
      "daily_total": 75
    }}
  ],
  "restaurants": {{
    "breakfast": [
      {{
        "name": "Café Name",
        "cuisine": "French",
        "price_per_person": 12,
        "rating": 4.5,
        "description": "Why to visit",
        "neighborhood": "Area name",
        "signature_dish": "Famous dish"
      }}
    ],
    "lunch": [
      {{
        "name": "Restaurant Name",
        "cuisine": "Italian",
        "price_per_person": 18,
        "rating": 4.6,
        "description": "Why to visit",
        "neighborhood": "Area name",
        "signature_dish": "Famous dish"
      }}
    ],
    "dinner": [
      {{
        "name": "Restaurant Name",
        "cuisine": "Local",
        "price_per_person": 35,
        "rating": 4.7,
        "description": "Why to visit",
        "neighborhood": "Area name",
        "signature_dish": "Famous dish"
      }}
    ]
  }},
  "budget_summary": {{
    "activities": 200,
    "food": 300,
    "transport": 50,
    "accommodation_estimate": 400,
    "total_estimate": 950
  }}
}}

Requirements:
- Include {duration_days} days in daily_itinerary
- Include 5-6 restaurants for EACH meal type (breakfast, lunch, dinner)
- Realistic prices in GBP
- Star ratings between 4.0-5.0
- User interests: {', '.join(keywords)}
- Budget: £{budget}
{hotel_info}

IMPORTANT: Respond ONLY with the JSON object. No markdown, no code blocks, no other text."""

        try:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            print(f"Raw AI response length: {len(response_text)}")
            
            # Clean JSON response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            response_text = response_text.strip()
            
            # Parse JSON
            itinerary_data = json.loads(response_text)
            
            # Validate required structure
            if "restaurants" not in itinerary_data:
                print("WARNING: No restaurants in response, adding defaults")
                itinerary_data["restaurants"] = self._get_default_restaurants(city_name)
            
            if "daily_itinerary" not in itinerary_data or len(itinerary_data["daily_itinerary"]) == 0:
                print("WARNING: No daily itinerary, adding defaults")
                itinerary_data["daily_itinerary"] = self._get_default_itinerary(city_name, duration_days)
            
            print(f"Successfully parsed itinerary with {len(itinerary_data.get('restaurants', {}).get('breakfast', []))} breakfast options")
            
            return itinerary_data
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return self._get_fallback_itinerary(city_name, duration_days)
        except Exception as e:
            print(f"Itinerary creation error: {e}")
            return self._get_fallback_itinerary(city_name, duration_days)
    
    def _get_default_restaurants(self, city_name):
        """Fallback restaurant data"""
        return {
            "breakfast": [
                {
                    "name": f"{city_name} Breakfast Café",
                    "cuisine": "Local",
                    "price_per_person": 12,
                    "rating": 4.5,
                    "description": "Popular local breakfast spot",
                    "neighborhood": "City Center",
                    "signature_dish": "Traditional breakfast"
                },
                {
                    "name": "Morning Bistro",
                    "cuisine": "Café",
                    "price_per_person": 10,
                    "rating": 4.3,
                    "description": "Cozy breakfast place",
                    "neighborhood": "Old Town",
                    "signature_dish": "Fresh pastries"
                },
                {
                    "name": "Early Bird Café",
                    "cuisine": "International",
                    "price_per_person": 14,
                    "rating": 4.4,
                    "description": "Great morning coffee and food",
                    "neighborhood": "Downtown",
                    "signature_dish": "Avocado toast"
                }
            ],
            "lunch": [
                {
                    "name": f"{city_name} Lunch Spot",
                    "cuisine": "Local",
                    "price_per_person": 18,
                    "rating": 4.6,
                    "description": "Great lunch location",
                    "neighborhood": "City Center",
                    "signature_dish": "Local specialties"
                },
                {
                    "name": "Lunch Bistro",
                    "cuisine": "International",
                    "price_per_person": 20,
                    "rating": 4.4,
                    "description": "Popular lunch venue",
                    "neighborhood": "Downtown",
                    "signature_dish": "Daily specials"
                },
                {
                    "name": "Midday Kitchen",
                    "cuisine": "Mediterranean",
                    "price_per_person": 22,
                    "rating": 4.5,
                    "description": "Fresh lunch options",
                    "neighborhood": "Harbor",
                    "signature_dish": "Grilled fish"
                }
            ],
            "dinner": [
                {
                    "name": f"{city_name} Fine Dining",
                    "cuisine": "Fine Dining",
                    "price_per_person": 45,
                    "rating": 4.8,
                    "description": "Upscale dinner experience",
                    "neighborhood": "City Center",
                    "signature_dish": "Chef's tasting menu"
                },
                {
                    "name": "Evening Restaurant",
                    "cuisine": "Local",
                    "price_per_person": 35,
                    "rating": 4.7,
                    "description": "Traditional dinner spot",
                    "neighborhood": "Old Town",
                    "signature_dish": "Regional dishes"
                },
                {
                    "name": "Night Table",
                    "cuisine": "Contemporary",
                    "price_per_person": 40,
                    "rating": 4.6,
                    "description": "Modern cuisine",
                    "neighborhood": "Arts District",
                    "signature_dish": "Seasonal menu"
                }
            ]
        }
    
    def _get_default_itinerary(self, city_name, days):
        """Fallback daily itinerary"""
        itinerary = []
        for day in range(1, days + 1):
            itinerary.append({
                "day": day,
                "theme": f"Day {day} Exploration",
                "morning": {
                    "time": "9:00 AM",
                    "activity": "Morning Activity",
                    "description": f"Explore {city_name} in the morning",
                    "cost": 15,
                    "duration": "2-3 hours",
                    "location": "City Center"
                },
                "afternoon": {
                    "time": "2:00 PM",
                    "activity": "Afternoon Activity",
                    "description": "Continue exploration",
                    "cost": 25,
                    "duration": "3-4 hours",
                    "location": "Main attractions"
                },
                "evening": {
                    "time": "7:00 PM",
                    "activity": "Evening Activity",
                    "description": "Evening entertainment",
                    "cost": 30,
                    "duration": "2-3 hours",
                    "location": "Entertainment district"
                },
                "daily_total": 70
            })
        return itinerary
    
    def _get_fallback_itinerary(self, city_name, duration_days):
        """Complete fallback itinerary structure"""
        return {
            "overview": {
                "destination": city_name,
                "best_time_to_visit": "Year-round",
                "getting_around": "Public transport and walking",
                "money_saving_tips": ["Use public transport", "Book attractions online", "Eat at local spots"],
                "local_customs": "Respect local customs and traditions"
            },
            "daily_itinerary": self._get_default_itinerary(city_name, duration_days),
            "restaurants": self._get_default_restaurants(city_name),
            "budget_summary": {
                "activities": 200,
                "food": 300,
                "transport": 50,
                "accommodation_estimate": 400,
                "total_estimate": 950
            }
        }
    
    def find_best_value_flights(self, flight_results):
        """Sort and filter flights by value"""
        if not flight_results:
            return []
        
        sorted_flights = sorted(flight_results, key=lambda x: x.get("price", float('inf')))
        prices = [f.get("price", 0) for f in flight_results if f.get("price")]
        avg_price = sum(prices) / len(prices) if prices else 0
        
        best_value = [f for f in sorted_flights if f.get("price", float('inf')) <= avg_price * 1.2]
        return best_value[:8]

agent = TravelPlanningAgent()

@app.route('/')
def home():
    try:
        return send_from_directory('.', 'index.html')
    except Exception as e:
        return jsonify({"message": "Travel Planning AI Agent", "error": str(e)})

@app.route('/itinerary', methods=['POST'])
def create_itinerary():
    data = request.json
    
    destination = data.get('destination')
    keywords = data.get('keywords', [])
    budget = data.get('budget', 1000)
    origin = data.get('origin')
    outbound_date = data.get('outbound_date')
    return_date = data.get('return_date')
    accommodation_type = data.get('accommodation_type', 'hotel')
    
    # Get proper city name for display
    destination_city = get_city_name(destination)
    
    print(f"\n=== NEW REQUEST ===")
    print(f"Destination Code: {destination}")
    print(f"Destination City: {destination_city}")
    print(f"Keywords: {keywords}")
    print(f"Budget: £{budget}")
    
    if not all([destination, origin, outbound_date]):
        return jsonify({"error": "Missing required fields"}), 400
    
    # Calculate trip duration
    if return_date:
        start = datetime.strptime(outbound_date, "%Y-%m-%d")
        end = datetime.strptime(return_date, "%Y-%m-%d")
        duration_days = (end - start).days
    else:
        duration_days = data.get('duration_days', 5)
        return_date = (datetime.strptime(outbound_date, "%Y-%m-%d") + timedelta(days=duration_days)).strftime("%Y-%m-%d")
    
    print(f"Trip duration: {duration_days} days")
    
    # Search flights
    all_flights = agent.analyze_flexible_dates(origin, destination, outbound_date, return_date, 7)
    best_flights = agent.find_best_value_flights(all_flights)
    print(f"Found {len(best_flights)} flight options")
    
    # Search accommodations (using proper city name)
    hotel_options = []
    airbnb_options = []
    
    if accommodation_type in ['hotel', 'mixed']:
        hotels = agent.search_hotels(destination, outbound_date, return_date)
        if hotels and "properties" in hotels:
            for hotel in hotels.get("properties", [])[:10]:
                hotel_options.append({
                    "name": hotel.get("name", "N/A"),
                    "price_per_night": hotel.get("rate_per_night", {}).get("lowest", "N/A"),
                    "total_price": hotel.get("total_rate", {}).get("lowest", "N/A"),
                    "rating": hotel.get("overall_rating", "N/A"),
                    "reviews": hotel.get("reviews", 0),
                    "link": hotel.get("link", "#"),
                    "description": hotel.get("description", "")[:200],
                    "images": hotel.get("images", [])[:3],
                    "amenities": hotel.get("amenities", [])[:5],
                    "type": "hotel"
                })
        print(f"Found {len(hotel_options)} hotels in {destination_city}")
    
    if accommodation_type in ['airbnb', 'mixed']:
        airbnb_listings = agent.search_airbnb(destination, outbound_date, return_date)
        for listing in airbnb_listings:
            airbnb_options.append({
                "name": listing.get("name"),
                "price_per_night": listing.get("price_per_night"),
                "total_price": listing.get("total_price"),
                "description": listing.get("description"),
                "link": listing.get("link"),
                "type": "airbnb",
                "property_type": listing.get("type")
            })
        print(f"Found {len(airbnb_options)} Airbnb options in {destination_city}")
    
    # Calculate costs
    flight_cost = best_flights[0].get('price', 0) if best_flights else 0
    remaining_budget = budget - flight_cost
    
    print(f"Creating itinerary with £{remaining_budget} remaining budget...")
    
    # Create itinerary (using proper city name)
    itinerary = agent.create_structured_itinerary(
        destination, 
        keywords, 
        remaining_budget, 
        duration_days, 
        hotels if accommodation_type in ['hotel', 'mixed'] else None
    )
    
    print(f"Itinerary created successfully!")
    print(f"- Breakfast options: {len(itinerary.get('restaurants', {}).get('breakfast', []))}")
    print(f"- Lunch options: {len(itinerary.get('restaurants', {}).get('lunch', []))}")
    print(f"- Dinner options: {len(itinerary.get('restaurants', {}).get('dinner', []))}")
    print(f"- Daily activities: {len(itinerary.get('daily_itinerary', []))}")
    
    response_data = {
        "destination": destination_city,  # Send city name to frontend
        "keywords": keywords,
        "total_budget": budget,
        "trip_duration": duration_days,
        "outbound_date": outbound_date,
        "return_date": return_date,
        "flight_options": best_flights,
        "recommended_flight_cost": flight_cost,
        "hotel_options": hotel_options,
        "airbnb_options": airbnb_options,
        "accommodation_type": accommodation_type,
        "remaining_budget": remaining_budget,
        "itinerary": itinerary
    }
    
    print(f"\n=== RESPONSE READY ===\n")
    
    return jsonify(response_data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
