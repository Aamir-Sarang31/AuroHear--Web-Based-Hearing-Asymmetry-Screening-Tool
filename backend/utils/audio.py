"""
Audio generation utilities for AuroHear application.
Handles tone generation for audiometric testing.
"""

import numpy as np
from io import BytesIO
from scipy.io.wavfile import write
from flask import Response

from backend.config import Config


def generate_tone_response(freq=1000, level_db=40, ear='both', duration=None):
    """
    Generate audio tone for audiometric testing.
    
    Args:
        freq (int): Frequency in Hz (20-20000)
        level_db (float): Level in dB HL
        ear (str): 'left', 'right', or 'both'
        duration (float): Duration in seconds
    
    Returns:
        Flask Response object with WAV audio data
    """
    try:
        if duration is None:
            duration = Config.AUDIO_DURATION
            
        if freq < 20 or freq > 20000:
            raise ValueError("Frequency out of audible range (20-20000 Hz)")

        # Server generates controlled baseline audio for audiometric testing
        # Client handles all dB HL to amplitude conversion for accurate audiometric control
        final_volume = 0.6  # Reduced baseline for better client-side control
        
        sample_rate = Config.SAMPLE_RATE
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        note = np.sin(2 * np.pi * freq * t) * final_volume

        # Apply fade in/out to prevent clicks
        fade_samples = int(sample_rate * 0.01)
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        note[:fade_samples] *= fade_in
        note[-fade_samples:] *= fade_out

        # Create stereo channels
        left_arr = np.zeros_like(note)
        right_arr = np.zeros_like(note)

        if ear == 'both':
            left_arr, right_arr = note, note
        elif ear == 'left':
            left_arr = note
        else:  # 'right'
            right_arr = note

        # Standard channel assignment: left channel first, right channel second
        audio = np.column_stack((left_arr, right_arr))

        # Maximum scaling for production environments - ensure audibility
        scaling_factor = 1.0  # Maximum scaling for production
        audio_int16 = (audio * 32767 * scaling_factor).astype(np.int16)
        
        # Ensure audio data is not empty or silent
        if np.max(np.abs(audio_int16)) == 0:
            # Create a minimum audible tone as fallback
            min_tone = np.sin(2 * np.pi * freq * t) * 0.3
            if ear == 'both':
                min_audio = np.column_stack((min_tone, min_tone))
            elif ear == 'left':
                min_audio = np.column_stack((min_tone, np.zeros_like(min_tone)))
            else:  # 'right'
                min_audio = np.column_stack((np.zeros_like(min_tone), min_tone))
            audio_int16 = (min_audio * 32767 * 0.5).astype(np.int16)

        # Create WAV file in memory
        bio = BytesIO()
        write(bio, sample_rate, audio_int16)
        bio.seek(0)
        
        audio_data = bio.getvalue()
        
        # Validate audio data
        if len(audio_data) < 100:  # WAV header should be at least 44 bytes + some data
            raise ValueError(f"Generated audio data too small: {len(audio_data)} bytes")
        
        # Add headers for better audio streaming and compatibility
        response = Response(audio_data, mimetype='audio/wav')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Content-Length'] = str(len(audio_data))
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Access-Control-Allow-Origin'] = '*'
        
        return response
        
    except Exception as e:
        raise ValueError(f"Error generating tone: {e}")


def validate_audio_parameters(freq, level_db, ear, duration):
    """
    Validate audio generation parameters.
    
    Args:
        freq: Frequency value to validate
        level_db: dB level to validate
        ear: Ear selection to validate
        duration: Duration to validate
    
    Returns:
        tuple: (validated_freq, validated_level_db, validated_ear, validated_duration)
    
    Raises:
        ValueError: If any parameter is invalid
    """
    # Validate frequency
    try:
        freq = int(freq)
        if freq < 20 or freq > 20000:
            raise ValueError("Frequency must be between 20 and 20000 Hz")
    except (ValueError, TypeError):
        raise ValueError("Frequency must be a valid integer")
    
    # Validate dB level
    try:
        level_db = float(level_db)
        if level_db < -10 or level_db > 80:
            raise ValueError("dB level must be between -10 and 80")
    except (ValueError, TypeError):
        raise ValueError("dB level must be a valid number")
    
    # Validate ear selection
    if ear not in ['left', 'right', 'both']:
        raise ValueError("Ear must be 'left', 'right', or 'both'")
    
    # Validate duration
    try:
        duration = float(duration)
        if duration <= 0 or duration > 5.0:
            raise ValueError("Duration must be between 0 and 5 seconds")
    except (ValueError, TypeError):
        raise ValueError("Duration must be a valid positive number")
    
    return freq, level_db, ear, duration