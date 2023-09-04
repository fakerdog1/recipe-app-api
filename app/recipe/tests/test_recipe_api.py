"""Test for recipe APIs"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPE_URL = reverse('recipe:recipe-list')

def detail_url(recipe_id):
    """Create and return detail url"""
    return reverse('recipe:recipe-detail', args=[recipe_id])

def create_recipe(user, **params):
    """Helper function to create a recipe"""
    defaults = {
        'title': 'Sample recipe',
        'description': 'Sample description',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'link': 'http://example.com/recipe.pdf'
    }
    
    defaults.update(params)
    recipe = Recipe.objects.create(user=user, **defaults)
    
    return recipe

def create_user(**params):
    """Helper function to create a user"""
    return get_user_model().objects.create_user(**params)

class PublicRecipeApiTests(TestCase):
    """Test unauthenticated recipe APIs"""
    
    def setUp(self):
        self.client = APIClient()
        
    def test_auth_required(self):
        """Test that authentication is required"""
        res = self.client.get(RECIPE_URL)
        
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        
class PrivateRecipeApiTests(TestCase):
    """Test authenticated recipe APIs"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='TestUser123@example.com',
            password='TestPass123',
        )   
        self.client.force_authenticate(self.user)
        
    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes"""
        create_recipe(user=self.user)
        create_recipe(user=self.user)
        
        res = self.client.get(RECIPE_URL)
        
        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        
    def test_recipes_limited_to_user(self):
        """Test retrieving recipes for user"""
        user2 = create_user(
            email='TestUser321@example.com',
            password='TestPass321'
        )
        
        create_recipe(user=user2)
        create_recipe(user=self.user)
        
        res = self.client.get(RECIPE_URL)
        
        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
    
    def test_get_recipe_detail(self):
        """Test retrieving a detail recipe"""
        recipe = create_recipe(user=self.user)
        
        url = detail_url(recipe.id)
        
        res = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        
    def test_create_recipe(self):
        """Test creating a recipe"""
        payload = {
            'title': 'Test Recipe',
            'time_minutes': 30,
            'price': Decimal('5.00')
        }
        
        res = self.client.post(RECIPE_URL, payload)
        
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        
        self.assertEqual(recipe.user, self.user)
        
    def test_partial_update_recipe(self):
        """Test updating a recipe"""
        original_link = "http://example.com/recipe.pdf"
        recipe = create_recipe(
            user=self.user, 
            title="sample title for recipe",
            link=original_link
        )
        
        payload = {
            'title': "New recipe title",
        }
        
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)
        
    def test_full_update_recipe(self):
        """Test updating a recipe"""
        recipe = create_recipe(
            user=self.user,
            title="sample title for recipe",
            link="http://example.com/recipe.pdf",
        )
        
        payload = {
            'title': "New recipe title",
            'description': "New recipe description",
            'time_minutes': 30,
            'price': Decimal('5.00'),
            'link': "http://example.com/new_recipe.pdf"
        }
        
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        
        for key, val in payload.items():
            self.assertEqual(getattr(recipe, key), val)
            
        self.assertEqual(recipe.user, self.user)
        
    def test_delete_recipe(self):
        """Test deleting a recipe"""
        reciper = create_recipe(user=self.user)
        
        url = detail_url(reciper.id)
        res = self.client.delete(url)
        
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=reciper.id).exists())
        
    def test_update_user_returns_error(self):
        """Test that updating user returns error"""
        recipe = create_recipe(user=self.user)
        new_user = create_user(email="newuser2@example.com", password="newpass2")
        
        payload = {
            'user': new_user.id
        }
        url = detail_url(recipe.id)
        
        self.client.patch(url, payload)
        
        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)
        
    def test_recipe_trying_to_delete_other_user_recipe_error(self):
        """Test that recipe cannot delete other user recipe"""
        new_user = create_user(email="newuser2@example.com", password="newpass2")
        recipe = create_recipe(user=new_user)
        
        url = detail_url(recipe.id)
        
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())