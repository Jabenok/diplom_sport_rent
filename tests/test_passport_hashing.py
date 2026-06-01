"""
Tests for passport data hashing functionality.
"""

import pytest
from app.models import User
from app import db


def test_set_passport_hashing(app):
    """Test that set_passport hashes the data"""
    with app.app_context():
        user = User(full_name="Test User", email="test@example.com")
        user.set_password("password123")
        user.set_passport("AB12345678")
        
        db.session.add(user)
        db.session.commit()
        
        # The hash should not be the plain text
        assert user.passport_hash != "AB12345678"
        # Hash should exist
        assert user.passport_hash is not None


def test_check_passport_valid(app):
    """Test that check_passport verifies correct passport data"""
    with app.app_context():
        user = User(full_name="Test User", email="test@example.com")
        user.set_password("password123")
        user.set_passport("AB12345678")
        
        db.session.add(user)
        db.session.commit()
        
        # Should verify correct passport
        assert user.check_passport("AB12345678") is True


def test_check_passport_invalid(app):
    """Test that check_passport rejects incorrect passport data"""
    with app.app_context():
        user = User(full_name="Test User", email="test@example.com")
        user.set_password("password123")
        user.set_passport("AB12345678")
        
        db.session.add(user)
        db.session.commit()
        
        # Should reject wrong passport
        assert user.check_passport("CD87654321") is False


def test_check_passport_none(app):
    """Test that check_passport returns False when no passport is set"""
    with app.app_context():
        user = User(full_name="Test User", email="test@example.com")
        user.set_password("password123")
        # Don't set passport
        
        db.session.add(user)
        db.session.commit()
        
        # Should return False for any input when no passport is set
        assert user.check_passport("AB12345678") is False


def test_set_passport_none(app):
    """Test that set_passport(None) clears the hash"""
    with app.app_context():
        user = User(full_name="Test User", email="test@example.com")
        user.set_password("password123")
        user.set_passport("AB12345678")
        
        db.session.add(user)
        db.session.commit()
        
        # Clear the passport
        user.set_passport(None)
        db.session.commit()
        
        assert user.passport_hash is None


def test_set_passport_empty_string(app):
    """Test that set_passport('') clears the hash"""
    with app.app_context():
        user = User(full_name="Test User", email="test@example.com")
        user.set_password("password123")
        user.set_passport("AB12345678")
        
        db.session.add(user)
        db.session.commit()
        
        # Clear with empty string
        user.set_passport("")
        db.session.commit()
        
        assert user.passport_hash is None


def test_passport_hash_different_each_time(app):
    """Test that the same passport generates different hashes (due to salt)"""
    with app.app_context():
        user1 = User(full_name="User 1", email="user1@example.com")
        user1.set_password("password123")
        user1.set_passport("AB12345678")
        
        user2 = User(full_name="User 2", email="user2@example.com")
        user2.set_password("password123")
        user2.set_passport("AB12345678")
        
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()
        
        # Different hashes for same input (due to salting)
        assert user1.passport_hash != user2.passport_hash
        # But both verify correctly
        assert user1.check_passport("AB12345678") is True
        assert user2.check_passport("AB12345678") is True


def test_passport_not_stored_in_plain_text(app):
    """Test that passport data is not stored in plain text in database"""
    with app.app_context():
        from sqlalchemy import text
        
        user = User(full_name="Test User", email="test@example.com")
        user.set_password("password123")
        user.set_passport("AB12345678")
        
        db.session.add(user)
        db.session.commit()
        
        # Query raw database
        result = db.session.execute(
            text("SELECT passport_hash FROM user WHERE email = 'test@example.com'")
        ).first()
        
        stored_hash = result[0]
        # Stored value should not be the plain text
        assert stored_hash != "AB12345678"
        # Should be a hash (werkzeug hashes start with pbkdf2: or scrypt:)
        assert stored_hash.startswith(('pbkdf2:', 'scrypt:', 'bcrypt:'))
