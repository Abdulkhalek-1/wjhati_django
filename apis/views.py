from django.shortcuts import render
from .serializers import *
from rest_framework import generics

from rest_framework.permissions import  AllowAny
class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
