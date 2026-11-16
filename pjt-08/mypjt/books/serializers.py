from rest_framework import serializers
from .models import Category, Book, Thread, Comment

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name')

class BookListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ('id', 'title', 'author', 'ISBN', 'cover')

class ThreadInBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Thread
        fields = ('id', 'title', 'content', 'reading_date')

class BookDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    threads = ThreadInBookSerializer(many=True, read_only=True)
    num_of_threads = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = (
            'id', 'category', 'title', 'description', 'ISBN', 
            'cover', 'publisher', 'pub_date', 'author', 
            'customer_review_rank', 'threads', 'num_of_threads'
        )

    def get_num_of_threads(self, obj):
        return obj.threads.count()

class BookTitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ('title',)

class ThreadListSerializer(serializers.ModelSerializer):
    book = BookTitleSerializer(read_only=True)
    class Meta:
        model = Thread
        fields = ('id', 'title', 'book')

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('id', 'thread', 'content', 'created_at', 'updated_at')
        read_only_fields = ('thread',)

class ThreadTitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Thread
        fields = ('title',)

class ThreadDetailSerializer(serializers.ModelSerializer):
    book = BookTitleSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    num_of_comments = serializers.SerializerMethodField()

    class Meta:
        model = Thread
        fields = (
            'id', 'book', 'title', 'content', 'reading_date', 
            'created_at', 'updated_at', 'comments', 'num_of_comments'
        )

    def get_num_of_comments(self, obj):
        return obj.comments.count()

class CommentDetailSerializer(serializers.ModelSerializer):
    thread = ThreadTitleSerializer(read_only=True)
    class Meta:
        model = Comment
        fields = ('id', 'thread', 'content', 'created_at', 'updated_at')
