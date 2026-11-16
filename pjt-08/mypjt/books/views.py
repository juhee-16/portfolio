from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Category, Book, Thread, Comment
from .serializers import (
    CategorySerializer, BookListSerializer, BookDetailSerializer,
    ThreadListSerializer, ThreadDetailSerializer, CommentSerializer,
    CommentDetailSerializer
)

@api_view(['GET'])
def category_list(request):
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def book_list(request):
    books = Book.objects.all()
    serializer = BookListSerializer(books, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def book_detail(request, book_pk):
    book = get_object_or_404(Book, pk=book_pk)
    serializer = BookDetailSerializer(book)
    return Response(serializer.data)

@api_view(['GET'])
def thread_list(request):
    threads = Thread.objects.all()
    serializer = ThreadListSerializer(threads, many=True)
    return Response(serializer.data)

@api_view(['GET', 'PUT', 'DELETE'])
def thread_detail(request, thread_pk):
    thread = get_object_or_404(Thread, pk=thread_pk)
    if request.method == 'GET':
        serializer = ThreadDetailSerializer(thread)
        return Response(serializer.data)
    elif request.method == 'PUT':
        serializer = ThreadDetailSerializer(thread, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        thread.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
def create_thread(request, book_pk):
    book = get_object_or_404(Book, pk=book_pk)
    serializer = ThreadDetailSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(book=book)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def create_comment(request, thread_pk):
    thread = get_object_or_404(Thread, pk=thread_pk)
    serializer = CommentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(thread=thread)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def comment_detail(request, comment_pk):
    comment = get_object_or_404(Comment, pk=comment_pk)
    if request.method == 'GET':
        serializer = CommentDetailSerializer(comment)
        return Response(serializer.data)
    elif request.method == 'PUT':
        serializer = CommentSerializer(comment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
