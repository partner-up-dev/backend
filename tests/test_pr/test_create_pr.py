"""Tests for creating partner requests"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import datetime

from run import app
from main.schemas.partner_request import PartnerRequestL2Type
from main.schemas.base.route import RouteItem, RouteItemDatetime


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_auth():
    """Mock authentication"""
    return Mock(user_id="test-user-123")


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = MagicMock()
    return session


class TestCreatePartnerRequest:
    """Test suite for creating partner requests"""

    def test_create_ride_hailing_pr(self, client, mock_auth, mock_db_session):
        """Test creating a ride-hailing partner request"""
        with patch("main.routes.require_auth", return_value=mock_auth):
            with patch("main.routes.get_db_session", return_value=mock_db_session):
                with patch("main.managers.partner_request.trip.ride_hailing.RideHailingPRManager.create") as mock_create:
                    mock_create.return_value = 123
                    
                    response = client.post(
                        "/partner_request/ride_hailing",
                        json={
                            "type": "ride_hailing",
                            "title": "Test Ride Hailing",
                            "introduction": "Test intro",
                            "route": [
                                {
                                    "location": "loc1",
                                    "datetime": {
                                        "datetime": datetime.datetime.now().isoformat(),
                                        "bring_ahead": 5,
                                        "put_off": 10
                                    }
                                },
                                {
                                    "location": "loc2",
                                    "datetime": {}
                                }
                            ],
                            "ride_hailing_preference": {
                                "ride_types": []
                            }
                        }
                    )
                    
                    assert response.status_code == 200
                    assert response.json() == 123
                    mock_create.assert_called_once()

    def test_create_commute_pr(self, client, mock_auth, mock_db_session):
        """Test creating a commute partner request"""
        with patch("main.routes.require_auth", return_value=mock_auth):
            with patch("main.routes.get_db_session", return_value=mock_db_session):
                with patch("main.managers.partner_request.trip.commute.CommutePRManager.create") as mock_create:
                    mock_create.return_value = 456
                    
                    response = client.post(
                        "/partner_request/commute",
                        json={
                            "type": "commute",
                            "title": "Test Commute",
                            "introduction": "Test intro",
                            "route": [
                                {
                                    "location": "loc1",
                                    "datetime": {
                                        "datetime": datetime.datetime.now().isoformat(),
                                        "bring_ahead": 5,
                                        "put_off": 10
                                    }
                                },
                                {
                                    "location": "loc2",
                                    "datetime": {}
                                }
                            ],
                            "on_at": "08:00:00",
                            "off_at": "18:00:00",
                            "workdays": ["monday", "tuesday", "wednesday", "thursday", "friday"]
                        }
                    )
                    
                    assert response.status_code == 200
                    assert response.json() == 456
                    mock_create.assert_called_once()

    def test_create_unsupported_type(self, client, mock_auth, mock_db_session):
        """Test creating partner request with unsupported type"""
        with patch("main.routes.require_auth", return_value=mock_auth):
            with patch("main.routes.get_db_session", return_value=mock_db_session):
                response = client.post(
                    "/partner_request/travel",
                    json={
                        "title": "Test Travel",
                        "introduction": "Test intro"
                    }
                )
                
                # Should fail because travel type is not implemented in create endpoint
                assert response.status_code == 400
                assert "Unsupported partner request type" in response.json()["detail"]


class TestPublishIdempotent:
    """Test suite for idempotent publish operation"""

    def test_publish_already_joinable(self, client, mock_auth, mock_db_session):
        """Test publishing a partner request that is already JOINABLE"""
        from main.schemas.partner_request import PartnerRequest, PartnerRequestStatus
        
        # Mock a PR that's already JOINABLE
        mock_pr = Mock(spec=PartnerRequest)
        mock_pr.id = 1
        mock_pr.status = PartnerRequestStatus.JOINABLE.value
        mock_pr.is_admin.return_value = True
        
        mock_db_session.get.return_value = mock_pr
        
        with patch("main.routes.require_auth", return_value=mock_auth):
            with patch("main.routes.get_db_session", return_value=mock_db_session):
                response = client.put("/partner_request/1/publish")
                
                assert response.status_code == 200
                # Should not call db.add or db.commit since already in target state
                mock_db_session.add.assert_not_called()
                mock_db_session.commit.assert_not_called()


class TestCancelIdempotent:
    """Test suite for idempotent cancel operation"""

    def test_cancel_already_cancelled(self, client, mock_auth, mock_db_session):
        """Test canceling a partner request that is already CANCELLED"""
        from main.schemas.partner_request import PartnerRequest, PartnerRequestStatus
        
        # Mock a PR that's already CANCELLED
        mock_pr = Mock(spec=PartnerRequest)
        mock_pr.id = 1
        mock_pr.status = PartnerRequestStatus.CANCELLED.value
        mock_pr.is_admin.return_value = True
        
        mock_db_session.get.return_value = mock_pr
        
        with patch("main.routes.require_auth", return_value=mock_auth):
            with patch("main.routes.get_db_session", return_value=mock_db_session):
                response = client.put("/partner_request/1/cancel")
                
                assert response.status_code == 200
                # Should not call db.add or db.commit since already in target state
                mock_db_session.add.assert_not_called()
                mock_db_session.commit.assert_not_called()


class TestNextStatusRemoved:
    """Test that next_status endpoint has been removed"""

    def test_next_status_endpoint_removed(self, client, mock_auth, mock_db_session):
        """Test that the next_status endpoint no longer exists"""
        with patch("main.routes.require_auth", return_value=mock_auth):
            with patch("main.routes.get_db_session", return_value=mock_db_session):
                response = client.put("/partner_request/1/status/next")
                
                # Should return 404 since the endpoint is removed
                assert response.status_code == 404
