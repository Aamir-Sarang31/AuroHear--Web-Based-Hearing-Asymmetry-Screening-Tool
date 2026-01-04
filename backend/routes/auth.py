"""
Authentication routes for AuroHear application.
Handles user registration, authentication status, and profile management.
"""

from flask import Blueprint, request, jsonify
from backend.database import db, supabase
from backend.models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user or sync with Supabase authentication"""
    data = request.json or {}
    
    # Extract user data
    name = data.get('name', '').strip()
    surname = data.get('surname', '').strip()
    age_group = data.get('age_group', '').strip()
    gender = data.get('gender', '').strip()
    supabase_id = data.get('supabase_id', '').strip()
    
    if not supabase_id:
        return jsonify({'error': 'Supabase ID required'}), 400
    
    try:
        # Check if user already exists
        existing_user = User.query.filter_by(supabase_id=supabase_id).first()
        
        if existing_user:
            # Update existing user
            existing_user.name = name
            existing_user.surname = surname
            existing_user.age_group = age_group
            existing_user.gender = gender
            existing_user.auth_type = 'authenticated'
            db.session.commit()
            
            return jsonify({
                'success': True,
                'user': existing_user.to_dict(),
                'message': 'User profile updated'
            })
        else:
            # Create new user
            new_user = User(
                name=name,
                surname=surname,
                age_group=age_group,
                gender=gender,
                supabase_id=supabase_id,
                auth_type='authenticated'
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'user': new_user.to_dict(),
                'message': 'User registered successfully'
            })
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500


@auth_bp.route('/status', methods=['GET'])
def auth_status():
    """Check authentication status and return user info if authenticated"""
    supabase_id = request.args.get('supabase_id')
    
    if not supabase_id:
        return jsonify({'authenticated': False}), 200
    
    try:
        user = User.query.filter_by(supabase_id=supabase_id).first()
        
        if user:
            return jsonify({
                'authenticated': True,
                'user': user.to_dict()
            })
        else:
            return jsonify({'authenticated': False}), 200
            
    except Exception as e:
        return jsonify({'error': f'Status check failed: {str(e)}'}), 500


@auth_bp.route('/profile', methods=['GET'])
def get_user_profile():
    """Get user profile information"""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get profile: {str(e)}'}), 500


@auth_bp.route('/profile', methods=['PUT'])
def update_user_profile():
    """Update user profile information"""
    data = request.json or {}
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update allowed fields
        if 'name' in data:
            user.name = data['name'].strip()
        if 'surname' in data:
            user.surname = data['surname'].strip()
        if 'age_group' in data:
            user.age_group = data['age_group'].strip()
        if 'gender' in data:
            user.gender = data['gender'].strip()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'message': 'Profile updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500