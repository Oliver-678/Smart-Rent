
from  concurrent import  futures
import  time
import logging
import  json
from  typing import Dict, List, Any
import numpy as np
from datetime import  datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s -%(name)s -%(levelname)s -%(message)s'
)

logger = logging.getLogger(__name__)


class RecommendationRequest:
    def __init__(self,user_id:str,financial_profile:Dict,preferences:Dict):
        self.user_id = user_id
        self.financial_profile = financial_profile
        self.preferences =preferences


class PropertyScore:
    def __init__(self,property_id:str,score:float,explanation:Dict):
        self.property_id = property_id
        self.score = score
        self.explanation = explanation

class RecommendationResponse:
    def __init__(self,recommendations:List[PropertyScore],metadata:Dict):
        self.recommendations = recommendations
        self.metadata = metadata


class RecommendationEngine:
    def __init__(self):
        self.RENT_TO_INCOME_RATIO = 0.30  # 30% rule
        self.LOCATION_WEIGHT = 0.30
        self.FINANCIAL_WEIGHT = 0.40
        self.LIFESTYLE_WEIGHT = 0.30

        def calculate_affordability(self,monthly_income:float,monthly_expenses:float,savings_goal:float)->float:
            disposable_income =monthly_income - monthly_expenses
            affordable_rent = min(monthly_income * self.RENT_TO_INCOME_RATIO,disposable_income - savings_goal)
            return  max(0,affordable_rent)

        def calculate_financial_score(self,property_rent:float,affordable_rent:float,montly_income:float)->float:
            if property_rent > affordable_rent:
                excess_ratio  = (property_rent - affordable_rent)/affordable_rent
                score = max(0, 100 - (excess_ratio*100))
            else:
                utilization = property_rent/affordable_rent
                score = 90 + (10 *(1-utilization))
            return min(100,max(0,score))

        def calculate_location_score(self,property_location:Dict,user_preferences:Dict)->float:
            score = 0
            max_score = 100

            if 'workplace' in user_preferences:
                distance =property_location.get('distance_to_workplace',float('inf'))
                if distance <=5:
                    score += 40
                elif distance <= 10:
                    score += 30
                elif distance <= 15:
                    score += 20
                else:
                    score +=10


            preferred_areas = user_preferences.get('preferred_areas',[])
            if property_location.get('neighborhood') in preferred_areas:
                score += 30

            transport_score = property_location.get('transport_score',0)
            score += (transport_score/10) *30

            return  min(max_score,score)

        def calculate_lifestyle_score(self,property_features:Dict,user_requirements:Dict)->float:
            score = 0
            total_requirements = 0

            required_bedrooms = user_requirements.get('bedrooms',1)
            property_bedrooms = property_features.get('bedrooms',0)

            if property_bedrooms >= required_bedrooms:
                score += 20
            total_requirements += 1

            required_amenities =set(user_requirements.get('amenities',[]))
            property_amenities = set(property_features.get('amenities',[]))

            if required_amenities:
                match_ratio = len(required_amenities & property_amenities)/len(required_amenities)
                score += match_ratio * 40
                total_requirements += 1

            if user_requirements.get('property_type') == property_features.get('type'):
                score += 20
            total_requirements += 1

            has_children = user_requirements.get('has_children',False)
            if has_children:
                if property_features.get('child_friendly',False):
                    score += 20
                total_requirements += 1
            return  score

        def generate_recommendations(self,request:RecommendationRequest,properties:List[Dict])->List[PropertyScore]:

            financial_profile = request.financial_profile
            preferences = request.preferences

            affordable_rent = self.calculate_affordability(
                financial_profile.get('monthly_income',0),
                financial_profile.get('monthly_expenses',0),
                financial_profile.get('savings_goal',0)
            )

            recommendations = []

            for prop in properties:
                financial_score = self.calculate_finanacial_score(
                    prop.get('rent',0),
                    affordable_rent,
                    financial_profile.get('monthly_income',0)
                )
                location_score = self.calculate_location_score(
                    prop.get('locations',{}),
                    preferences
                )
                lifestyle_score = self.calculate_lifestyle_score(
                    prop.get('features',{}),
                    preferences
                )
                total_score = (
                    financial_score * self.FINANCIAL_WEIGHT +
                    location_score * self.LOCATION_WEIGHT +
                    lifestyle_score * self.LIFESTYEL_SCORE
                )

                # Generate explanation
                explanation = {
                    'financial_score': round(financial_score, 2),
                    'location_score': round(location_score, 2),
                    'lifestyle_score': round(lifestyle_score, 2),
                    'affordable_rent': round(affordable_rent, 2),
                    'property_rent': prop.get('rent', 0),
                    'rent_to_income_ratio': round(
                        prop.get('rent', 0) / financial_profile.get('monthly_income', 1) * 100, 2
                    )
                }

                recommendations.append(PropertyScore(
                    property_id=prop.get('id'),
                    score=total_score,
                    explanation=explanation
                ))

                #Sort by score descending
                recommendations.sort(key = lambda x: x.score,reverse = True)

                return  recommendations


class RecommendationServicer:
    """
    gRPC service handler for recommendation requests
    """

    def __init__(self):
        self.engine = RecommendationEngine()
        self.request_count = 0
        logger.info("RecommendationServicer initialized")

    def GetRecommendations(self, request_data: Dict, context=None) -> Dict:
        """
        Main RPC method for getting property recommendations
        """
        start_time = time.time()
        self.request_count += 1
        request_id = f"REQ-{self.request_count}-{int(start_time)}"

        try:
            logger.info(f"Processing request {request_id} for user {request_data.get('user_id')}")

            # Parse request
            request = RecommendationRequest(
                user_id=request_data.get('user_id'),
                financial_profile=request_data.get('financial_profile', {}),
                preferences=request_data.get('preferences', {})
            )

            # Get properties (in production, fetch from database)
            properties = self._get_properties(request.preferences)

            # Generate recommendations
            recommendations = self.engine.generate_recommendations(request, properties)

            # Prepare response
            response_data = {
                'request_id': request_id,
                'user_id': request.user_id,
                'recommendations': [
                    {
                        'property_id': rec.property_id,
                        'score': round(rec.score, 2),
                        'explanation': rec.explanation
                    }
                    for rec in recommendations[:10]  # Top 10
                ],
                'metadata': {
                    'total_properties_analyzed': len(properties),
                    'processing_time_ms': round((time.time() - start_time) * 1000, 2),
                    'timestamp': datetime.utcnow().isoformat(),
                    'algorithm_version': '1.0.0'
                }
            }

            logger.info(f"Request {request_id} completed in {response_data['metadata']['processing_time_ms']}ms")

            return response_data

        except Exception as e:
            logger.error(f"Error processing request {request_id}: {str(e)}", exc_info=True)
            raise

    def _get_properties(self, preferences: Dict) -> List[Dict]:
        """
        Fetch properties from database (mock implementation)
        In production, this would query PostgreSQL/Elasticsearch
        """
        # Mock properties for demonstration
        return [
            {
                'id': 'PROP-001',
                'rent': 150000,
                'location': {
                    'neighborhood': 'Bastos',
                    'distance_to_workplace': 3.5,
                    'transport_score': 8.5
                },
                'features': {
                    'bedrooms': 2,
                    'type': 'apartment',
                    'amenities': ['parking', 'security', 'water'],
                    'child_friendly': True
                }
            },
            {
                'id': 'PROP-002',
                'rent': 200000,
                'location': {
                    'neighborhood': 'Bonanjo',
                    'distance_to_workplace': 7.2,
                    'transport_score': 7.0
                },
                'features': {
                    'bedrooms': 3,
                    'type': 'apartment',
                    'amenities': ['parking', 'security', 'generator'],
                    'child_friendly': True
                }
            },
            {
                'id': 'PROP-003',
                'rent': 120000,
                'location': {
                    'neighborhood': 'Omnisport',
                    'distance_to_workplace': 5.0,
                    'transport_score': 6.5
                },
                'features': {
                    'bedrooms': 1,
                    'type': 'studio',
                    'amenities': ['security', 'water'],
                    'child_friendly': False
                }
            }
        ]


# ==================== HTTP/REST Wrapper (Alternative to gRPC) ====================

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse


class RecommendationHTTPHandler(BaseHTTPRequestHandler):
    """
    HTTP REST API wrapper for the recommendation service
    Alternative to gRPC for simpler integration
    """

    servicer = RecommendationServicer()

    def do_POST(self):
        """Handle POST requests to /recommend"""
        if self.path == '/recommend':
            try:
                # Read request body
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))

                # Process recommendation
                response_data = self.servicer.GetRecommendations(request_data)

                # Send response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))

            except Exception as e:
                logger.error(f"Error handling request: {str(e)}", exc_info=True)
                self.send_error(500, str(e))
        else:
            self.send_error(404, 'Not Found')

    def do_GET(self):
        """Handle GET requests for health check"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            health_data = {
                'status': 'healthy',
                'service': 'recommendation-engine',
                'timestamp': datetime.utcnow().isoformat(),
                'requests_processed': self.servicer.request_count
            }
            self.wfile.write(json.dumps(health_data).encode('utf-8'))
        else:
            self.send_error(404, 'Not Found')

    def log_message(self, format, *args):
        """Override to use custom logger"""
        logger.info(f"{self.client_address[0]} - {format % args}")


# ==================== Server Startup ====================

def serve_http(port=8080):
    """
    Start HTTP REST API server
    """
    server_address = ('', port)
    httpd = HTTPServer(server_address, RecommendationHTTPHandler)
    logger.info(f"HTTP REST API server listening on port {port}")
    logger.info(f"Endpoints:")
    logger.info(f"  POST /recommend - Get property recommendations")
    logger.info(f"  GET  /health    - Health check")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        httpd.shutdown()


def serve_grpc(port=50051):
    """
    Start gRPC server (requires grpcio to be installed)
    """
    try:
        import grpc
        from concurrent import futures

        # This would use generated proto stubs in production
        # For now, showing the structure
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        # server.add_RecommendationServicer_to_server(RecommendationServicer(), server)
        server.add_insecure_port(f'[::]:{port}')
        server.start()

        logger.info(f"gRPC server listening on port {port}")
        server.wait_for_termination()

    except ImportError:
        logger.error("grpcio not installed. Install with: pip install grpcio grpcio-tools")
        logger.info("Falling back to HTTP REST API...")
        serve_http(8080)


if __name__ == '__main__':
    import sys

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║           OLISTAY RECOMMENDATION RPC SERVER               ║
    ║                                                           ║
    ║  Smart Rental Recommendation Platform for Cameroon       ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    mode = sys.argv[1] if len(sys.argv) > 1 else 'http'

    if mode == 'grpc':
        serve_grpc(50051)
    else:
        serve_http(8080)