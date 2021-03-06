from django.conf.urls import include,url

from . import views
from rest_framework import routers

router = routers.DefaultRouter()

urlpatterns = [
    url(r'^auth/login', views.LoginEp),
    url(r'^auth/signup', views.SignUpEp),
    url(r'^auth/logout', views.LogoutEp),
    url(r'^auth/closeup', views.CloseUpEp),
    url(r'^auth/password-reset', views.PassResetEp),
    url(r'^auth/request-password-reset', views.PassResetRequestEp),
    url(r'^recipes', views.RecipeListEp.as_view()),
    url(r'^recipe/(?P<recipeId>[_0-9]+)', views.RecipeEp.as_view()),
    url(r'^shopping-list/(?P<shoppingListId>[_0-9]+)/recipe/(?P<recipeId>[0-9]+)', views.ShoppingRecipeItemEp.as_view()),
    url(r'^shopping-list/(?P<shoppingListId>[_0-9]+)', views.ShoppingListEp.as_view()),
    url(r'^ingredients', views.IngredientListEp.as_view()),  
    url(r'^ingredient/(?P<ingredientId>[_0-9]+)', views.IngredientEp.as_view()),
    url(r'^ingredientbyname/(?P<ingredientName>.+)', views.IngredientByNameEp.as_view()),
    url(r'^shops', views.ShopListEp.as_view()),
    url(r'^shop/current', views.CurrentShopEp.as_view()), 
    url(r'^shop/(?P<shopId>[_0-9]+)', views.ShopEp.as_view()), 
    url(r'^locations', views.LocationListEp.as_view()), 
    url(r'^location/(?P<locationId>[_0-9]+)', views.LocationEp.as_view()),
    url(r'^stats', views.StatsEp.as_view()),
    url(r'^', include(router.urls)),    
]