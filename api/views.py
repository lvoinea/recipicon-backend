from .models import Recipe, RecipeIngredient, Ingredient, ShoppingList, ShoppingItem, UserProfile, IngredientLocation, Shop, Location
from .serializers import RecipeSerializer, FullRecipeSerializer, IngredientSerializer, ShoppingListSerializer, IngredientLocationSerializer, ShopSerializer, LocationSerializer
from .permissions import IsOwner
from .authentications import CsrfExemptTokenAuthentication

from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth import authenticate, login, logout

from django.shortcuts import get_object_or_404

from django.db.models import Model

from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from django.http import JsonResponse
 
#{"username":"jhon","password":"papa"} 

@api_view(['POST'])
@authentication_classes((CsrfExemptTokenAuthentication,))
@csrf_exempt
def LoginEp(request):
    """
    Authenticates a user
    """
    username = request.data['username']
    password = request.data['password']
    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            login(request, user)
            token = Token.objects.get_or_create(user=user)
            return Response(token[0].key, status=status.HTTP_200_OK)
        else:
            return Response('Account has been disabled', status=status.HTTP_403_FORBIDDEN)            
    else:
        return Response('Invalid login combination', status=status.HTTP_401_UNAUTHORIZED)
        
@api_view(['GET'])
def LogoutEp(request):
    """
    Logout a user
    """
    if request.user.is_authenticated():
        token = Token.objects.get_or_create(user=request.user)
        token[0].delete()
    logout(request)
    return Response('User logged out', status=status.HTTP_200_OK)
 
class RecipeListEp(APIView):
    permission_classes = (IsAuthenticated,IsOwner)
    
    def get(self, request, format=None):    
        #return recipes
        user = self.request.user
        recipes = Recipe.objects.filter(user__username=user.username)
        recipeIds = [recipe.id for recipe in recipes]
        
        # get shopping list
        userProfile = get_object_or_404(UserProfile,user__username=user.username)            
        shoppingList = userProfile.shoppingList
        items = shoppingList.items.filter(recipe_id__in = recipeIds)
        
        selectedRecipeIds = set([item.recipe.id for item in items])
        for recipe in recipes:
            if recipe.id in selectedRecipeIds:
                recipe.in_shopping_list = True
            else:
                recipe.in_shopping_list = False
        
        serializer = RecipeSerializer(recipes, many=True)
        return Response(serializer.data)   
        
class RecipeEp(APIView):
    permission_classes = (IsAuthenticated, IsOwner,)
    
    #return recipe together with ingredients and presence in the shopping list
    def get(self, request, recipeId, format=None):    
        
        recipe = get_object_or_404(Recipe, pk=recipeId)
        self.check_object_permissions(self.request, recipe)
        
        # Check if the recipe is in the current shopping list
        recipe.in_shopping_list = False        
        user = self.request.user
        userProfile = get_object_or_404(UserProfile,user__username=user.username)            
        shoppingList = userProfile.shoppingList
        items = shoppingList.items.filter(recipe_id = recipeId)
        if (len(items) == 1):
            recipe.in_shopping_list = True       
        
        serializer = FullRecipeSerializer(recipe)
        return Response(serializer.data)
        
    def delete(self, request, recipeId, format=None):
        recipe = get_object_or_404(Recipe, pk=recipeId)
        self.check_object_permissions(self.request, recipe)
        recipe.delete()
        return Response(status.HTTP_204_NO_CONTENT)       
    
    def post(self, request, recipeId, format=None):
    
        user = self.request.user
        
        newRecipe = request.data;        
        if not Utils.isValidRecipe(newRecipe):
            return Response('Unkonwn recipe data', status=status.HTTP_400_BAD_REQUEST)        
        
        #------------------------------- Update recipe            
        # recipe exists
        if (newRecipe['id'] != '_'):                       
            oldRecipe = get_object_or_404(Recipe, pk=newRecipe['id'])
        # recipe is new
        else :
            oldRecipe = Recipe(user=user)
            oldRecipe.save()
        
        oldRecipe.name = newRecipe['name']
        oldRecipe.category = newRecipe['category']
        oldRecipe.description = newRecipe['description']
        oldRecipe.serves = newRecipe['serves']
        oldRecipe.duration = newRecipe['duration']
        oldRecipe.image = newRecipe['image']
            
        #------------------------------- Update ingredients 
        #- Remove deleted recipe ingredient relations
        newRecipeIngredientIds = set([])
        for newRecipeIngredient in newRecipe['recipe_ingredients']:          
            if not Utils.isValidRecipeIngredient(newRecipeIngredient):
                return Response('Unkonwn recipe ingredient data: '+ str(newRecipeIngredient), status=status.HTTP_400_BAD_REQUEST)
            else:
                newRecipeIngredient['id'] = str(newRecipeIngredient['id'])
                newRecipeIngredientIds.add(newRecipeIngredient['id'])
        #print newRecipeIngredientIds
        
        dOldRecipeIngredients = {}
        for oldRecipeIngredient in oldRecipe.recipe_ingredients.all():
            oldRecipeIngredientId = str(oldRecipeIngredient.id)
            if not oldRecipeIngredientId in newRecipeIngredientIds:
                oldRecipeIngredient.delete()
                #print 'delete recipe ingredient :'+ oldRecipeIngredientId
            else:
                dOldRecipeIngredients[oldRecipeIngredientId] = oldRecipeIngredient
        
        
        #- Add new recipe ingredient relations
        for newRecipeIngredient in newRecipe['recipe_ingredients']:            
            if newRecipeIngredient['id'].startswith('_'):         
                oldRecipeIngredient = RecipeIngredient(recipe=oldRecipe)
            else:
                oldRecipeIngredient = dOldRecipeIngredients[str(newRecipeIngredient['id'])]
                      
            oldRecipeIngredient.unit = newRecipeIngredient['unit']
            oldRecipeIngredient.quantity = newRecipeIngredient['quantity'] 
            oldRecipeIngredient.ingredient = Ingredient.objects.get(id=newRecipeIngredient['ingredient'], user=user)
            oldRecipeIngredient.save()
            
        #------------------------------- Save recipe  
        oldRecipe.save()
        
        # Check if the recipe is in the current shopping list
        oldRecipe.in_shopping_list = False        
        userProfile = get_object_or_404(UserProfile,user__username=user.username)            
        shoppingList = userProfile.shoppingList
        items = shoppingList.items.filter(recipe_id = oldRecipe.id)
        if (len(items) == 1):
            oldRecipe.in_shopping_list = True
        serializer = FullRecipeSerializer(oldRecipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
class IngredientListEp(APIView):
    permission_classes = (IsAuthenticated,IsOwner)
    
    def get(self, request, format=None):    
        user = self.request.user
        ingredients = user.ingredients
        serializer = IngredientLocationSerializer(ingredients, many=True)
        return Response(serializer.data)
        
class IngredientEp(APIView):
    permission_classes = (IsAuthenticated,IsOwner)
    
    def get(self, request, ingredientId, format=None):    
        
        user = self.request.user
        ingredient = get_object_or_404(Ingredient, pk=ingredientId)
        self.check_object_permissions(self.request, ingredient)
        
        serializer = IngredientLocationSerializer(ingredient)
        return Response(serializer.data)
        
    def post(self, request, ingredientId, format=None):    
        
        user = self.request.user        
        newIngredient = request.data
       
        if not Utils.isValidIngredient(newIngredient):
            return Response('Unkonwn ingredient data', status=status.HTTP_400_BAD_REQUEST)   
        
        if (str(newIngredient['id']).startswith('_')):
            ingredient = Ingredient(user=user)
            ingredient.save()
        else:
            ingredient = Ingredient.objects.get(id=newIngredient['id'])
            
        ingredient.name = newIngredient['name']

        locations = Location.objects.filter(id__in = newIngredient['locations']) 
        newLocationIds = [location.id for location in locations]
        ingredientLocations = IngredientLocation.objects.filter(ingredient__id= ingredientId)
        oldLocationIds = [ingredientLocation.location.id for ingredientLocation in ingredientLocations]

        newIngredientLocations = []
        # delete removed locations
        for ingredientLocation in ingredientLocations:
            if not (ingredientLocation.location.id in newLocationIds):
                ingredientLocation.delete()
            else:
                newIngredientLocations.append(ingredientLocation)
        # add new locations
        for location in locations:
            if not (location.id in oldLocationIds):
                ingredientLocation = IngredientLocation(location = location, ingredient = ingredient)
                ingredientLocation.save()
                newIngredientLocations.append(ingredientLocation)

        ingredient.locations.set(newIngredientLocations)
        ingredient.save()
   
        serializer = IngredientLocationSerializer(ingredient)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
class IngredientByNameEp(APIView):
    permission_classes = (IsAuthenticated,IsOwner)
    
    def get(self, request, ingredientName, format=None):
        
        user = self.request.user
        ingredient = get_object_or_404(Ingredient, name=ingredientName, user__username=user.username)
        self.check_object_permissions(self.request, ingredient)
        
        serializer = IngredientLocationSerializer(ingredient)
        return Response(serializer.data)

    def put(self, request, ingredientName, format=None):
        
        user = self.request.user
        ingredient = Ingredient(user=user, name=ingredientName)
        ingredient.save()

        serializer = IngredientLocationSerializer(ingredient)
        return Response(serializer.data)

class ShoppingListEp(APIView):
    permission_classes = (IsAuthenticated,IsOwner)
    
    # Use id = '_' to get thhe current shopping list from the user profile
    def get(self, request, shoppingListId, format=None):
        if (shoppingListId == '_'):
            user = self.request.user
            userProfile = get_object_or_404(UserProfile,user__username=user.username)            
            shoppingList = userProfile.shoppingList
        else:
            shoppingList = get_object_or_404(ShoppingList, pk=shoppingListId)
            
        self.check_object_permissions(self.request, shoppingList)
        serializer = ShoppingListSerializer(shoppingList)
        return Response(serializer.data)
    
    # Use id = '_' to create a new shopping list and register it in the user profile 
    def post(self, request, shoppingListId, format=None):    
        user = self.request.user
        
        newShoppingList = request.data;        
        if not Utils.isValidShoppingList(newShoppingList):
            return Response('Unkonwn shopping list data', status=status.HTTP_400_BAD_REQUEST)   
        
        #---------------------------- Update existing shopping list ---
        if (shoppingListId != '_'):                       
            shoppingList = get_object_or_404(ShoppingList, pk=shoppingListId)
            shoppingList.name = newShoppingList['name']
            
            #- Remove deleted items
            newShoppingItems = set([])
            for newItem in newShoppingList['items']:
                if not Utils.isValidShoppingItem(newItem):
                    return Response('Unkonwn shopping list item data: '+ str(newItem), status=status.HTTP_400_BAD_REQUEST)
                else:
                    newItem['id'] = str(newItem['id'])
                    newShoppingItems.add(newItem['id'])
            
            dOldShoppingItems = {}
            for oldShoppingItem in shoppingList.items.all():
                oldShoppingItemId = str(oldShoppingItem.id)
                if not oldShoppingItemId in newShoppingItems:
                    oldShoppingItem.delete()
                    #print 'delete shopping item :'+ oldShoppingItemId
                else:
                    dOldShoppingItems[oldShoppingItemId] = oldShoppingItem
        
            #- Add new items
            for newItem in newShoppingList['items']:           
                if newItem['id'].startswith('_'):         
                    shoppingItem = ShoppingItem(shoppingList = shoppingList)
                else:
                    shoppingItem = dOldShoppingItems[str(newItem['id'])]
                    
                shoppingItem.unit = newItem['unit']
                shoppingItem.quantity = newItem['quantity']                
                # ingredient items are created if they do not exist already
                if (newItem['ingredient'] is not None):
                    shoppingItem.recipe = None
                    shoppingItem.ingredient = Ingredient.objects.get(pk=newItem['ingredient'], user=user)
                # recipe items have to exist already or an error will be raised
                # 10.10.2016: this assumes shoppping lists can be edited by adding recipes - currently not used
                elif (newItem['recipe'] is not None):
                    shoppingItem.ingredient = None
                    shoppingItem.recipe = get_object_or_404(Recipe, pk=newItem['recipe']['id'])
                shoppingItem.save()
            
        #--------------------------------- Create new shopping list ---
        else :
            shoppingList = ShoppingList(user=user)  
            shoppingList.save()
            
            # Make this the current shopping list in the user profile
            userProfile = get_object_or_404(UserProfile,user__username=user.username)
            userProfile.shoppingList = shoppingList
            userProfile.save()   
            
            # Clone all items (if any) - can be used to create a new shopping list starting from an old one
            for newItem in newShoppingList['items']:
                shoppingItem = ShoppingItem(unit = newItem['unit'], quantity = newItem['quantity'], shoppingList = shoppingList)
                # ingredient items are created if they do not exist already
                if (newItem['ingredient'] is not None):
                    shoppingItem.recipe = None
                    shoppingItem.ingredient = Ingredient.objects.get(pk=newItem['ingredient'], user=user)
                # recipe items have to exist already or an error will be raised
                elif (newItem['recipe'] is not None):
                    shoppingItem.ingredient = None
                    shoppingItem.recipe = get_object_or_404(Recipe, pk=newItem['recipe']['id'])
                shoppingItem.save()
                shoppingList.items.add(shoppingItem)         
               
        
        shoppingList.save()
        serializer = ShoppingListSerializer(shoppingList)
        return Response(serializer.data)  
        
class ShoppingRecipeItemEp(APIView):
    permission_classes = (IsAuthenticated,IsOwner)

    # use shoppingListId = '_' to search for recipe in the current shopping list
    def get(self, request, shoppingListId, recipeId, format=None):
        
        result = False
        user = self.request.user
        
        # get shopping list
        if (shoppingListId == '_'):  
            userProfile = get_object_or_404(UserProfile,user__username=user.username)            
            shoppingList = userProfile.shoppingList
        else:
            shoppingList = get_object_or_404(ShoppingList, pk=shoppingListId)
        self.check_object_permissions(self.request, shoppingList)
            
        # find item
        items = shoppingList.items.filter(recipe_id = recipeId)
        if (len(items) == 1):
            result = True
            
        return Response(result)
        
    def post(self, request, shoppingListId, recipeId, format=None):
        command = request.data        
        
        if not Utils.isValidShoppingItemCmd(command):
            return Response('Unkonwn command format.', status=status.HTTP_400_BAD_REQUEST)
        
        # get shopping list
        user = self.request.user
        if (shoppingListId == '_'):  
            userProfile = get_object_or_404(UserProfile,user__username=user.username)            
            shoppingList = userProfile.shoppingList
        else:
            shoppingList = get_object_or_404(ShoppingList, pk=shoppingListId)
        self.check_object_permissions(self.request, shoppingList)
        
        # find shopping item
        shoppingItem = None
        items = shoppingList.items.filter(recipe_id = recipeId)
        if (len(items) == 1):
            shoppingItem = items[0]
        
        response = None
        if (command['action'] == 'add'):
            if shoppingItem is not None:
                response = 'already in list'
            else:
                shoppingItem = ShoppingItem(shoppingList = shoppingList)
                shoppingItem.ingredient = None
                shoppingItem.recipe = get_object_or_404(Recipe, pk=recipeId)
                shoppingItem.unit = 'serve'
                shoppingItem.quantity = shoppingItem.recipe.serves
                shoppingItem.save()
                response = 'added'
        elif (command['action'] == 'remove'):
            if shoppingItem is None:
                response = 'not in list'                
            else:
                shoppingItem.delete()
                response = 'removed'
        else:
            return Response('Unkonwn command: '+ str(command['action']), status=status.HTTP_400_BAD_REQUEST)
        
        return Response(response) 

class ShopListEp(APIView):
    permission_classes = (IsAuthenticated,IsOwner)
    
    def get(self, request, format=None):
        user = self.request.user
        shops = user.shops
        serializer = ShopSerializer(shops, many=True)
        return Response(serializer.data)

class ShopEp(APIView):
    permission_classes = (IsAuthenticated,IsOwner)
    
    def get(self, request, shopId, format=None):
    
        if (shopId == '_'):
            user = self.request.user
            userProfile = get_object_or_404(UserProfile,user__username=user.username)            
            shop = userProfile.shop
        else:
            shop = get_object_or_404(Shop, pk=shopId)
            
        serializer = ShopSerializer(shop)
        return Response(serializer.data)
        
    def post(self, request, shopId, format=None):
    
        user = self.request.user        
        newShop = request.data
        
        if (str(newShop['id']).startswith('_')):
            shop = Shop(user=user)
            shop.save()            
        else:
            shop = get_object_or_404(Shop, pk=newShop['id'])
            
        shop.name = newShop['name']
        shop.save()
        
        serializer = ShopSerializer(shop)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, shopId, format=None):
        
        try:
            val = int(shopId)
        except ValueError:
            return Response('Unkonwn shop', status=status.HTTP_400_BAD_REQUEST)    
        
        shop = get_object_or_404(Shop, pk=shopId)
        self.check_object_permissions(self.request, shop)
        shop.delete()

        return Response(status.HTTP_204_NO_CONTENT)

class CurrentShopEp(APIView):

    permission_classes = (IsAuthenticated,IsOwner)
    
    def get(self, request, format=None):
    
        user = self.request.user
        userProfile = get_object_or_404(UserProfile,user__username=user.username)
        shop = userProfile.shop
            
        serializer = ShopSerializer(shop)
        return Response(serializer.data)
        
    def post(self, request, format=None):
    
        user = self.request.user        
        newCurrentShop = request.data
        
        userProfile = get_object_or_404(UserProfile,user__username=user.username)
        shop = None
        if (newCurrentShop['id'] is not None):
            shop = get_object_or_404(Shop,pk=newCurrentShop['id'])            
        userProfile.shop = shop
        userProfile.save()
            
        serializer = ShopSerializer(shop)
        return Response(serializer.data)
        
class LocationListEp(APIView):

    permission_classes = (IsAuthenticated,IsOwner)
    
    def get(self, request, format=None):
        user = self.request.user
        locations = user.locations
        serializer = LocationSerializer(locations, many=True)
        return Response(serializer.data)
        
class LocationEp(APIView):
    permission_classes = (IsAuthenticated,IsOwner)
    
    def get(self, request, locationId, format=None):
    
        try:
            val = int(locationId)
        except ValueError:
            return Response('Unkonwn location', status=status.HTTP_400_BAD_REQUEST)
        
        location = get_object_or_404(Location, pk=locationId)
        self.check_object_permissions(request, location)
            
        serializer = LocationSerializer(location)
        return Response(serializer.data)
        
    def post(self, request, locationId, format=None):
    
        user = self.request.user        
        newLocation = request.data
        
        shop = get_object_or_404(Shop,pk=newLocation['shop'])
        self.check_object_permissions(request, shop)
        
        if (locationId.startswith('_')):
            location = Location(user=user,shop=shop)
            location.save()            
        else:
            location = get_object_or_404(Location, pk=locationId)
            self.check_object_permissions(request, location)
            location.shop = shop        
        
        location.name = newLocation['name']
        location.save()
        
        serializer = LocationSerializer(location)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    def delete(self, request, locationId, format=None):
        
        try:
            val = int(locationId)
        except ValueError:
            return Response('Unkonwn location', status=status.HTTP_400_BAD_REQUEST)    
    
        location = get_object_or_404(Location, pk=locationId)
        self.check_object_permissions(self.request, location)
        location.delete()
        return Response(status.HTTP_204_NO_CONTENT)  

class StatsEp(APIView):
    permission_classes = (IsAuthenticated,IsOwner)
    
    def get(self, request, format=None):
        user = self.request.user

        recipes = Recipe.objects.filter(user__username=user.username)

        stats = {}

        #--- Recipes
        statsRecipes = []
        _stats = {}
        for recipe in recipes:
            category = recipe.category            
            if (category == ''):
                category = "other"
            if category in _stats:
                _stats[category] += 1
            else:
                _stats[category] = 1
        for k in _stats:
            statsRecipes.append({'category':k, 'recipes':_stats[k]})
        stats['recipes'] = statsRecipes
        stats['recipe_number'] = len(recipes)

        #---
        return JsonResponse(stats)
        
class Utils():

    @staticmethod
    def isValidRecipeIngredient(ingredient):
        return set(ingredient.keys()).issubset(set(['id', 'ingredient', 'unit', 'quantity']))
    
    @staticmethod
    def isValidIngredient(ingredient):
        return set(ingredient.keys()).issubset(set(['id', 'name', 'locations']))
    
    
    @staticmethod
    def isValidRecipe(recipe):
        return set(recipe.keys()).issubset(set(['id', 'name', 'category', 'description', 'serves', 'duration', 'recipe_ingredients','in_shopping_list','image']))
     
    @staticmethod
    def isValidShoppingList(shoppingList):
        return set(shoppingList.keys()).issubset(set(['id', 'name', 'date', 'items']))
     
    @staticmethod
    def isValidShoppingItem(shoppingItem):
        return set(shoppingItem.keys()).issubset(set(['id', 'unit', 'quantity', 'ingredient', 'recipe']))

    @staticmethod
    def isValidShoppingItemCmd(shoppingItem):
        return set(shoppingItem.keys()).issubset(set(['action']))
     
