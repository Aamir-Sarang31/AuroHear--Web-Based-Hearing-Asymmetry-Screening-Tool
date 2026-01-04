"""
Main routes for AuroHear application.
Handles the main page and basic navigation.
"""

from flask import Blueprint, render_template
from backend.database import supabase
from backend.config import Config

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Main application page"""
    return render_template('index.html', 
                         supabase_url=Config.SUPABASE_URL, 
                         supabase_key=Config.SUPABASE_KEY)


@main_bp.route('/favicon.ico')
def favicon():
    """Favicon route to prevent 404 errors"""
    from flask import Response
    return Response(status=204)