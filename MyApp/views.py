from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CommentForm, LostFoundForm, ProfileForm, RegistrationForm
from .models import Comment, LostAndFoundItem


@login_required
def index(request):
    """Create a lost item report for the signed-in user."""
    if request.method == 'POST':
        form = LostFoundForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.status = 'Open'
            item.save()
            return redirect('item_detail', item_id=item.item_id)
    else:
        form = LostFoundForm()

    return render(
        request,
        'MyApp/LostFound_form.html',
        {'form': form, 'page_mode': 'report_form'},
    )


def item_list(request):
    """Display searchable lost item reports with an optional status filter."""
    search_text = request.GET.get('q', '').strip()
    selected_status = request.GET.get('status', 'Open')
    items = LostAndFoundItem.objects.select_related('owner').order_by('-date_lost_found')

    if search_text:
        items = items.filter(
            Q(item_name__icontains=search_text)
            | Q(description__icontains=search_text)
            | Q(category__icontains=search_text)
            | Q(location__icontains=search_text)
        )

    if selected_status not in ('Open', 'Resolved'):
        selected_status = 'Open'
    items = items.filter(status=selected_status)

    return render(
        request,
        'MyApp/LostFound_list.html',
        {
            'items': items,
            'page_mode': 'item_list',
            'search_text': search_text,
            'selected_status': selected_status,
        },
    )


def item_detail(request, item_id):
    """Show a report and its comments."""
    item = get_object_or_404(
        LostAndFoundItem.objects.select_related('owner'),
        pk=item_id,
    )
    comment_form = CommentForm()
    return render(
        request,
        'MyApp/LostFound_list.html',
        {
            'item': item,
            'comment_form': comment_form,
            'page_mode': 'item_detail',
        },
    )


@login_required
def item_edit(request, item_id):
    """Let only the report owner update its details."""
    item = get_object_or_404(LostAndFoundItem, pk=item_id, owner=request.user)
    if request.method == 'POST':
        form = LostFoundForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect('item_detail', item_id=item.item_id)
    else:
        form = LostFoundForm(instance=item)

    return render(
        request,
        'MyApp/LostFound_form.html',
        {'form': form, 'item': item, 'page_mode': 'item_edit'},
    )


@login_required
def item_confirm_delete(request, item_id):
    """Let only the report owner delete their report."""
    item = get_object_or_404(LostAndFoundItem, pk=item_id, owner=request.user)

    if request.method == 'POST':
        item.delete()
        return redirect('dashboard')

    return render(
        request,
        'MyApp/LostFound_confirm_delete.html',
        {'item': item},
    )


@login_required
def add_comment(request, item_id):
    """Add a comment only while the lost item report is open."""
    item = get_object_or_404(LostAndFoundItem, pk=item_id)
    if item.status != 'Open':
        return redirect('item_detail', item_id=item.item_id)

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.item = item
            comment.user = request.user
            comment.save()
            return redirect('item_detail', item_id=item.item_id)

        return render(
            request,
            'MyApp/LostFound_list.html',
            {
                'item': item,
                'comment_form': form,
                'page_mode': 'item_detail',
            },
        )
    return redirect('item_detail', item_id=item.item_id)


@login_required
def comment_edit(request, comment_id):
    """Let only the comment author edit their comment."""
    comment = get_object_or_404(Comment, pk=comment_id, user=request.user)
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('item_detail', item_id=comment.item.item_id)
    else:
        form = CommentForm(instance=comment)

    return render(
        request,
        'MyApp/LostFound_form.html',
        {
            'form': form,
            'item': comment.item,
            'comment': comment,
            'page_mode': 'comment_edit',
        },
    )


@login_required
@require_POST
def comment_delete(request, comment_id):
    """Let only the comment author delete their comment."""
    comment = get_object_or_404(Comment, pk=comment_id, user=request.user)
    item_id = comment.item.item_id
    comment.delete()
    return redirect('item_detail', item_id=item_id)


@login_required
@require_POST
def mark_resolved(request, item_id):
    """Let the report owner mark an item as returned."""
    item = get_object_or_404(LostAndFoundItem, pk=item_id, owner=request.user)
    item.status = 'Resolved'
    item.save(update_fields=['status'])
    return redirect('item_detail', item_id=item.item_id)


@login_required
def dashboard(request):
    """Show the signed-in user's own reports."""
    items = LostAndFoundItem.objects.filter(owner=request.user).order_by('-date_lost_found')
    return render(
        request,
        'MyApp/LostFound_list.html',
        {'items': items, 'page_mode': 'dashboard'},
    )


@login_required
def profile(request):
    """Show and update basic account details."""
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)

    return render(
        request,
        'MyApp/LostFound_form.html',
        {'form': form, 'page_mode': 'profile'},
    )


def register(request):
    """Register a new account and sign the user in."""
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('item_list')
    else:
        form = RegistrationForm()

    return render(
        request,
        'MyApp/LostFound_form.html',
        {'form': form, 'page_mode': 'register'},
    )


class LostFoundLoginView(LoginView):
    template_name = 'MyApp/LostFound_form.html'
    authentication_form = AuthenticationForm
    extra_context = {'page_mode': 'login'}


class LostFoundLogoutView(LogoutView):
    next_page = 'item_list'