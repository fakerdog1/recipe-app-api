"""
Test for the tags API
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag

from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')

def detail_url(tag_id):
    """Create and return a tag detail url"""
    return reverse('recipe:tag-detail', args=[tag_id])

def create_user(email="testemail@example.com", password="Testpass123"):
    """Helper function to create a user"""
    return get_user_model().objects.create_user(email=email, password=password)

class PublicTagsApiTests(TestCase):
    """Test the publicly available tags API"""
    def setUp(self):
        self.client = APIClient()
        
    def test_login_required(self):
        """Test that login is required for retrieving tags"""
        res = self.client.get(TAGS_URL)
        
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        
class PrivateTagsApiTests(TestCase):
    """Tests the private tags API"""
    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        
    def test_retrieve_tags(self):
        """Test retrieving tags"""
        Tag.objects.create(user=self.user, name="Vegan")
        Tag.objects.create(user=self.user, name="Dessert")
        
        res = self.client.get(TAGS_URL)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)
        
        self.assertEqual(res.data, serializer.data)
        
    def test_tags_limited_to_user(self):
        """Test tags limited to user"""
        user2 = create_user(email="user2@example.com", password="Testpass123")
        
        Tag.objects.create(user=user2, name="Fruity")
        tag = Tag.objects.create(user=self.user, name="Comfort Food")
        
        res = self.client.get(TAGS_URL)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)
        
    def test_update_tag(self):
        """Test updating a tag"""
        tag = Tag.objects.create(user=self.user, name="Test Tag")
        
        payload = {'name': 'New Tag Name'}
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])
        
    def test_delete_tag(self):
        """Test deleting a tag"""
        tag = Tag.objects.create(user=self.user, name="Test Tag")
        
        res = self.client.delete(detail_url(tag.id))
        
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tag = Tag.objects.filter(user=self.user)
        self.assertFalse(tag.exists())
        
    def test_other_user_cannot_delete_tag(self):
        """Test other user cannot delete tag"""
        user2 = create_user(email="user2@example.com", password="Testpass123")
        tag = Tag.objects.create(user=user2, name="Test Tag")
        
        res = self.client.delete(detail_url(tag.id))
        
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        tag = Tag.objects.filter(id=tag.id)
        self.assertTrue(tag.exists())