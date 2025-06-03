from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Count, Max
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST, require_http_methods
from django.template.loader import render_to_string
import json
import uuid
from datetime import timedelta

from .models import (
    ChatRoom, ChatRoomMembership, Message, MessageReaction,
    Announcement, AnnouncementRead, ExternalIntegration,
    ExternalMessage, MessageTemplate, CommunicationLog
)
from .forms import (
    ChatRoomForm, MessageForm, ReactionForm, AnnouncementForm,
    ExternalIntegrationForm, MessageTemplateForm
)

# Helper functions
def user_can_access_room(user, room):
    """Check if user can access a chat room"""
    if room.is_private:
        return room.members.filter(id=user.id).exists() or room.created_by == user
    return True

def user_has_room_admin_rights(user, room):
    """Check if user has admin rights in a room"""
    if room.created_by == user:
        return True
    try:
        membership = ChatRoomMembership.objects.get(room=room, user=user)
        return membership.role in ['ADMIN', 'MODERATOR']
    except ChatRoomMembership.DoesNotExist:
        return False

def log_communication_activity(log_type, user, description, **kwargs):
    """Log communication activity"""
    log = CommunicationLog(
        log_type=log_type,
        user=user,
        description=description,
    )

    # Add related objects if provided
    if 'chat_room' in kwargs:
        log.chat_room = kwargs['chat_room']
    if 'message' in kwargs:
        log.message = kwargs['message']
    if 'announcement' in kwargs:
        log.announcement = kwargs['announcement']
    if 'metadata' in kwargs:
        log.metadata = kwargs['metadata']

    log.save()
    return log

# Chat Room Views
@login_required
def chat_rooms_list(request):
    """List all chat rooms the user has access to"""
    # Get user's rooms (either member or public)
    user_rooms = ChatRoom.objects.filter(
        Q(members=request.user) | Q(is_private=False)
    ).distinct().order_by('-updated_at')

    # Add unread count for each room
    for room in user_rooms:
        try:
            membership = ChatRoomMembership.objects.get(room=room, user=request.user)
            last_read = membership.last_read_at
            if last_read:
                room.unread_count = room.messages.filter(created_at__gt=last_read).count()
            else:
                room.unread_count = room.messages.count()
        except ChatRoomMembership.DoesNotExist:
            room.unread_count = 0

    # Split rooms into pinned and regular
    pinned_rooms = []
    regular_rooms = []

    for room in user_rooms:
        try:
            membership = ChatRoomMembership.objects.get(room=room, user=request.user)
            if membership.is_pinned:
                pinned_rooms.append(room)
            else:
                regular_rooms.append(room)
        except ChatRoomMembership.DoesNotExist:
            regular_rooms.append(room)

    return render(request, 'communication/chat_rooms_list.html', {
        'pinned_rooms': pinned_rooms,
        'regular_rooms': regular_rooms,
    })

@login_required
def chat_room_detail(request, room_id):
    """Display a chat room with its messages"""
    room = get_object_or_404(ChatRoom, id=room_id)

    # Check if user can access this room
    if not user_can_access_room(request.user, room):
        messages.error(request, "You don't have access to this chat room.")
        return redirect('communication:chat_rooms_list')

    # Get or create membership for the user
    membership, created = ChatRoomMembership.objects.get_or_create(
        room=room,
        user=request.user,
        defaults={'role': 'MEMBER'}
    )

    # Log user join if newly created
    if created:
        log_communication_activity(
            'USER_JOINED',
            request.user,
            f"{request.user.username} joined chat room '{room.name}'",
            chat_room=room
        )

    # Update last read time
    membership.last_read_at = timezone.now()
    membership.save()

    # Get most recent messages (pagination will be handled by AJAX)
    recent_messages = room.messages.filter(is_deleted=False).order_by('-created_at')[:20]
    recent_messages = reversed(list(recent_messages))  # Reverse to show in chronological order

    # Get message reactions
    for message in recent_messages:
        message.user_reactions = message.reactions.filter(user=request.user)
        message.all_reactions = message.reactions.all().values('reaction').annotate(count=Count('reaction'))

    # Get room members with their roles
    members = room.chatroommbership_set.select_related('user').all()

    # Check if user has admin rights
    is_admin = user_has_room_admin_rights(request.user, room)

    # Prepare message form
    message_form = MessageForm()

    return render(request, 'communication/chat_room_detail.html', {
        'room': room,
        'messages': recent_messages,
        'members': members,
        'is_admin': is_admin,
        'message_form': message_form,
    })

@login_required
def chat_room_create(request):
    """Create a new chat room"""
    if request.method == 'POST':
        form = ChatRoomForm(request.POST, user=request.user)
        if form.is_valid():
            chat_room = form.save(commit=False)
            chat_room.created_by = request.user
            chat_room.save()

            # Add creator as a member and admin
            ChatRoomMembership.objects.create(
                room=chat_room,
                user=request.user,
                role='ADMIN'
            )

            # Log the creation
            log_communication_activity(
                'USER_JOINED',
                request.user,
                f"Created new chat room '{chat_room.name}'",
                chat_room=chat_room
            )

            messages.success(request, f"Chat room '{chat_room.name}' created successfully.")
            return redirect('communication:chat_room_detail', room_id=chat_room.id)
    else:
        form = ChatRoomForm(user=request.user)

    return render(request, 'communication/chat_room_form.html', {
        'form': form,
        'title': 'Create Chat Room'
    })

@login_required
def chat_room_edit(request, room_id):
    """Edit an existing chat room"""
    room = get_object_or_404(ChatRoom, id=room_id)

    # Check if user has admin rights
    if not user_has_room_admin_rights(request.user, room):
        messages.error(request, "You don't have permission to edit this chat room.")
        return redirect('communication:chat_room_detail', room_id=room.id)

    if request.method == 'POST':
        form = ChatRoomForm(request.POST, user=request.user, instance=room)
        if form.is_valid():
            form.save()
            messages.success(request, f"Chat room '{room.name}' updated successfully.")
            return redirect('communication:chat_room_detail', room_id=room.id)
    else:
        form = ChatRoomForm(user=request.user, instance=room)

    return render(request, 'communication/chat_room_form.html', {
        'form': form,
        'room': room,
        'title': 'Edit Chat Room'
    })

@login_required
def chat_room_members(request, room_id):
    """Manage chat room members"""
    room = get_object_or_404(ChatRoom, id=room_id)

    # Check if user has admin rights
    if not user_has_room_admin_rights(request.user, room):
        messages.error(request, "You don't have permission to manage room members.")
        return redirect('communication:chat_room_detail', room_id=room.id)

    memberships = ChatRoomMembership.objects.filter(room=room).select_related('user')

    return render(request, 'communication/chat_room_members.html', {
        'room': room,
        'memberships': memberships
    })

@login_required
@require_POST
def chat_room_add_member(request, room_id):
    """Add a member to a chat room"""
    room = get_object_or_404(ChatRoom, id=room_id)

    # Check if user has admin rights
    if not user_has_room_admin_rights(request.user, room):
        messages.error(request, "You don't have permission to add members.")
        return redirect('communication:chat_room_members', room_id=room.id)

    user_id = request.POST.get('user_id')
    role = request.POST.get('role', 'MEMBER')

    try:
        user = User.objects.get(id=user_id)

        # Check if user is already a member
        if room.members.filter(id=user.id).exists():
            messages.warning(request, f"{user.username} is already a member of this room.")
        else:
            # Check if room has reached max members
            if room.members.count() >= room.max_members:
                messages.error(request, f"Cannot add more members. Maximum limit of {room.max_members} reached.")
            else:
                # Add user to room
                ChatRoomMembership.objects.create(
                    room=room,
                    user=user,
                    role=role
                )

                # Log the addition
                log_communication_activity(
                    'USER_JOINED',
                    request.user,
                    f"Added {user.username} to chat room '{room.name}'",
                    chat_room=room,
                    metadata={'added_user_id': user.id}
                )

                messages.success(request, f"{user.username} added to the room successfully.")
    except User.DoesNotExist:
        messages.error(request, "User not found.")

    return redirect('communication:chat_room_members', room_id=room.id)

@login_required
@require_POST
def chat_room_remove_member(request, room_id, user_id):
    """Remove a member from a chat room"""
    room = get_object_or_404(ChatRoom, id=room_id)
    user_to_remove = get_object_or_404(User, id=user_id)

    # Check if user has admin rights
    if not user_has_room_admin_rights(request.user, room):
        messages.error(request, "You don't have permission to remove members.")
        return redirect('communication:chat_room_members', room_id=room.id)

    # Prevent removing the room creator
    if user_to_remove == room.created_by:
        messages.error(request, "Cannot remove the room creator.")
        return redirect('communication:chat_room_members', room_id=room.id)

    # Remove membership
    try:
        membership = ChatRoomMembership.objects.get(room=room, user=user_to_remove)
        membership.delete()

        # Log the removal
        log_communication_activity(
            'USER_LEFT',
            request.user,
            f"Removed {user_to_remove.username} from chat room '{room.name}'",
            chat_room=room,
            metadata={'removed_user_id': user_to_remove.id}
        )

        messages.success(request, f"{user_to_remove.username} removed from the room.")
    except ChatRoomMembership.DoesNotExist:
        messages.error(request, "User is not a member of this room.")

    return redirect('communication:chat_room_members', room_id=room.id)

@login_required
@require_POST
def chat_room_update_role(request, room_id, user_id):
    """Update a member's role in a chat room"""
    room = get_object_or_404(ChatRoom, id=room_id)
    user_to_update = get_object_or_404(User, id=user_id)

    # Check if user has admin rights
    if not user_has_room_admin_rights(request.user, room):
        messages.error(request, "You don't have permission to update member roles.")
        return redirect('communication:chat_room_members', room_id=room.id)

    # Prevent updating the room creator's role
    if user_to_update == room.created_by:
        messages.error(request, "Cannot update the room creator's role.")
        return redirect('communication:chat_room_members', room_id=room.id)

    new_role = request.POST.get('role')
    if new_role not in [role[0] for role in ChatRoomMembership.MEMBER_ROLES]:
        messages.error(request, "Invalid role specified.")
        return redirect('communication:chat_room_members', room_id=room.id)

    # Update membership
    try:
        membership = ChatRoomMembership.objects.get(room=room, user=user_to_update)
        old_role = membership.role
        membership.role = new_role
        membership.save()

        # Log the role update
        log_communication_activity(
            'USER_JOINED',
            request.user,
            f"Updated {user_to_update.username}'s role from {old_role} to {new_role} in '{room.name}'",
            chat_room=room,
            metadata={'user_id': user_to_update.id, 'old_role': old_role, 'new_role': new_role}
        )

        messages.success(request, f"{user_to_update.username}'s role updated to {new_role}.")
    except ChatRoomMembership.DoesNotExist:
        messages.error(request, "User is not a member of this room.")

    return redirect('communication:chat_room_members', room_id=room.id)

@login_required
@require_POST
def chat_room_archive(request, room_id):
    """Archive or unarchive a chat room"""
    room = get_object_or_404(ChatRoom, id=room_id)

    # Check if user has admin rights
    if not user_has_room_admin_rights(request.user, room):
        messages.error(request, "You don't have permission to archive this room.")
        return redirect('communication:chat_room_detail', room_id=room.id)

    # Toggle archive status
    room.is_archived = not room.is_archived
    room.save()

    action = "archived" if room.is_archived else "unarchived"

    # Log the archive action
    log_communication_activity(
        'USER_LEFT' if room.is_archived else 'USER_JOINED',
        request.user,
        f"Chat room '{room.name}' {action} by {request.user.username}",
        chat_room=room,
        metadata={'action': action}
    )

    messages.success(request, f"Chat room {action} successfully.")
    return redirect('communication:chat_rooms_list')

# Message Views
@login_required
def load_messages(request, room_id):
    """Load messages for a chat room (for pagination/infinite scroll)"""
    room = get_object_or_404(ChatRoom, id=room_id)

    # Check if user can access this room
    if not user_can_access_room(request.user, room):
        return JsonResponse({'error': "You don't have access to this chat room."}, status=403)

    # Get parameters
    before_id = request.GET.get('before_id')
    limit = int(request.GET.get('limit', 20))

    # Query messages
    messages_query = room.messages.filter(is_deleted=False)

    if before_id:
        try:
            before_message = Message.objects.get(id=before_id)
            messages_query = messages_query.filter(created_at__lt=before_message.created_at)
        except (Message.DoesNotExist, ValueError):
            pass

    messages_list = messages_query.order_by('-created_at')[:limit]
    messages_list = reversed(list(messages_list))  # Reverse for chronological order

    # Add reactions to messages
    for message in messages_list:
        message.user_reactions = message.reactions.filter(user=request.user)
        message.all_reactions = message.reactions.all().values('reaction').annotate(count=Count('reaction'))

    # Render messages to HTML
    html = render_to_string('communication/partials/messages_list.html', {
        'messages': messages_list,
        'room': room,
        'user': request.user
    })

    return JsonResponse({
        'html': html,
        'has_more': messages_query.count() > limit
    })

@login_required
@require_POST
def send_message(request, room_id):
    """Send a new message to a chat room"""
    room = get_object_or_404(ChatRoom, id=room_id)

    # Check if user can access this room
    if not user_can_access_room(request.user, room):
        return JsonResponse({'error': "You don't have access to this chat room."}, status=403)

    # Process the form
    form = MessageForm(request.POST, request.FILES)
    if form.is_valid():
        message = form.save(commit=False)
        message.room = room
        message.sender = request.user

        # Handle file attachments
        if request.FILES.get('file_attachment'):
            file_obj = request.FILES['file_attachment']
            message.file_name = file_obj.name
            message.file_size = file_obj.size

            # Determine message type based on file type
            file_ext = file_obj.name.split('.')[-1].lower()
            if file_ext in ['jpg', 'jpeg', 'png', 'gif']:
                message.message_type = 'IMAGE'
            elif file_ext in ['mp3', 'wav', 'ogg']:
                message.message_type = 'VOICE'
            else:
                message.message_type = 'FILE'

        # Set reply-to if provided
        reply_to_id = request.POST.get('reply_to')
        if reply_to_id:
            try:
                reply_to = Message.objects.get(id=reply_to_id)
                if reply_to.room == room:  # Only allow replies in the same room
                    message.reply_to = reply_to
            except Message.DoesNotExist:
                pass

        message.save()

        # Update room's updated_at time
        room.updated_at = timezone.now()
        room.save()

        # Update the sender's membership last_read_at
        try:
            membership = ChatRoomMembership.objects.get(room=room, user=request.user)
            membership.last_read_at = timezone.now()
            membership.save()
        except ChatRoomMembership.DoesNotExist:
            pass

        # Log the message
        log_communication_activity(
            'MESSAGE_SENT',
            request.user,
            f"Sent message in '{room.name}'",
            chat_room=room,
            message=message
        )

        # Render the new message
        message.user_reactions = []
        message.all_reactions = []

        html = render_to_string('communication/partials/message_item.html', {
            'message': message,
            'room': room,
            'user': request.user
        })

        return JsonResponse({
            'status': 'success',
            'html': html,
            'message_id': str(message.id)
        })
    else:
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

@login_required
@require_http_methods(['POST', 'GET'])
def edit_message(request, room_id, message_id):
    """Edit an existing message"""
    room = get_object_or_404(ChatRoom, id=room_id)
    message = get_object_or_404(Message, id=message_id, room=room)

    # Check if user is the message sender or has admin rights
    if message.sender != request.user and not user_has_room_admin_rights(request.user, room):
        return JsonResponse({'error': "You don't have permission to edit this message."}, status=403)

    if request.method == 'POST':
        # Update the message content
        content = request.POST.get('content')
        if content:
            message.content = content
            message.is_edited = True
            message.updated_at = timezone.now()
            message.save()

            # Log the edit
            log_communication_activity(
                'MESSAGE_SENT',
                request.user,
                f"Edited message in '{room.name}'",
                chat_room=room,
                message=message
            )

            # Render the updated message
            message.user_reactions = message.reactions.filter(user=request.user)
            message.all_reactions = message.reactions.all().values('reaction').annotate(count=Count('reaction'))

            html = render_to_string('communication/partials/message_item.html', {
                'message': message,
                'room': room,
                'user': request.user
            })

            return JsonResponse({
                'status': 'success',
                'html': html
            })
        else:
            return JsonResponse({'status': 'error', 'error': 'Message content cannot be empty'}, status=400)
    else:
        # Return a form for editing
        return render(request, 'communication/partials/edit_message_form.html', {
            'message': message,
            'room': room
        })

@login_required
@require_POST
def delete_message(request, room_id, message_id):
    """Delete (soft delete) a message"""
    room = get_object_or_404(ChatRoom, id=room_id)
    message = get_object_or_404(Message, id=message_id, room=room)

    # Check if user is the message sender or has admin rights
    if message.sender != request.user and not user_has_room_admin_rights(request.user, room):
        return JsonResponse({'error': "You don't have permission to delete this message."}, status=403)

    # Soft delete the message
    message.is_deleted = True
    message.content = "[This message was deleted]"
    message.save()

    # Log the deletion
    log_communication_activity(
        'MESSAGE_SENT',
        request.user,
        f"Deleted message in '{room.name}'",
        chat_room=room,
        message=message
    )

    return JsonResponse({'status': 'success'})

@login_required
@require_POST
def pin_message(request, room_id, message_id):
    """Pin or unpin a message"""
    room = get_object_or_404(ChatRoom, id=room_id)
    message = get_object_or_404(Message, id=message_id, room=room)

    # Check if user has admin rights
    if not user_has_room_admin_rights(request.user, room):
        return JsonResponse({'error': "You don't have permission to pin messages."}, status=403)

    # Toggle pin status
    message.is_pinned = not message.is_pinned
    message.save()

    action = "pinned" if message.is_pinned else "unpinned"

    # Log the pin action
    log_communication_activity(
        'MESSAGE_SENT',
        request.user,
        f"Message {action} in '{room.name}'",
        chat_room=room,
        message=message,
        metadata={'action': action}
    )

    return JsonResponse({'status': 'success', 'isPinned': message.is_pinned})

@login_required
@require_POST
def react_to_message(request, room_id, message_id):
    """Add or remove a reaction to a message"""
    room = get_object_or_404(ChatRoom, id=room_id)
    message = get_object_or_404(Message, id=message_id, room=room)

    # Check if user can access this room
    if not user_can_access_room(request.user, room):
        return JsonResponse({'error': "You don't have access to this chat room."}, status=403)

    reaction_emoji = request.POST.get('reaction')

    # Validate the reaction emoji
    valid_reactions = [choice[0] for choice in MessageReaction.REACTION_TYPES]
    if reaction_emoji not in valid_reactions:
        return JsonResponse({'error': "Invalid reaction."}, status=400)

    # Check if the reaction already exists
    existing_reaction = MessageReaction.objects.filter(
        message=message,
        user=request.user,
        reaction=reaction_emoji
    ).first()

    if existing_reaction:
        # Remove the reaction
        existing_reaction.delete()
        action = 'removed'
    else:
        # Add the reaction
        MessageReaction.objects.create(
            message=message,
            user=request.user,
            reaction=reaction_emoji
        )
        action = 'added'

    # Get updated reactions
    user_reactions = message.reactions.filter(user=request.user)
    all_reactions = message.reactions.all().values('reaction').annotate(count=Count('reaction'))

    # Render the updated reactions
    html = render_to_string('communication/partials/message_reactions.html', {
        'message': message,
        'user_reactions': user_reactions,
        'all_reactions': all_reactions
    })

    return JsonResponse({
        'status': 'success',
        'action': action,
        'html': html
    })

# Announcement Views
@login_required
def announcements_list(request):
    """List all announcements relevant to the user"""
    user = request.user

    # Get announcements for this user (targeted directly, via department, or all users)
    announcements = Announcement.objects.filter(
        Q(target_all_users=True) |
        Q(target_users=user) |
        Q(target_departments=user.userprofile.department)
    ).distinct()

    # Add read status to each announcement
    for announcement in announcements:
        announcement.is_read = AnnouncementRead.objects.filter(
            announcement=announcement,
            user=user
        ).exists()

    # Filter by type if requested
    announcement_type = request.GET.get('type')
    if announcement_type:
        announcements = announcements.filter(announcement_type=announcement_type)

    # Paginate results
    paginator = Paginator(announcements, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Get announcement types for filtering
    announcement_types = dict(Announcement.ANNOUNCEMENT_TYPES)

    return render(request, 'communication/announcements_list.html', {
        'page_obj': page_obj,
        'announcement_types': announcement_types,
        'selected_type': announcement_type
    })

@login_required
def announcement_detail(request, announcement_id):
    """Display a single announcement"""
    announcement = get_object_or_404(Announcement, id=announcement_id)
    user = request.user

    # Check if user has access to this announcement
    if not (announcement.target_all_users or
            announcement.target_users.filter(id=user.id).exists() or
            (hasattr(user, 'userprofile') and user.userprofile.department and
             announcement.target_departments.filter(id=user.userprofile.department.id).exists())):
        messages.error(request, "You don't have access to this announcement.")
        return redirect('communication:announcements_list')

    # Mark as read if not already
    AnnouncementRead.objects.get_or_create(
        announcement=announcement,
        user=user
    )

    # Get the read count
    read_count = announcement.read_by.count()

    return render(request, 'communication/announcement_detail.html', {
        'announcement': announcement,
        'read_count': read_count,
        'can_edit': announcement.created_by == user,
    })

@login_required
def announcement_create(request):
    """Create a new announcement"""
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()

            # Save many-to-many relationships
            form.save_m2m()

            # Publish immediately if requested
            if announcement.is_published:
                # Log the publication
                log_communication_activity(
                    'ANNOUNCEMENT_PUBLISHED',
                    request.user,
                    f"Published announcement: {announcement.title}",
                    announcement=announcement
                )

            messages.success(request, "Announcement created successfully.")
            return redirect('communication:announcement_detail', announcement_id=announcement.id)
    else:
        form = AnnouncementForm(user=request.user)

    return render(request, 'communication/announcement_form.html', {
        'form': form,
        'title': 'Create Announcement'
    })

@login_required
def announcement_edit(request, announcement_id):
    """Edit an existing announcement"""
    announcement = get_object_or_404(Announcement, id=announcement_id)

    # Check if user is the creator
    if announcement.created_by != request.user:
        messages.error(request, "You don't have permission to edit this announcement.")
        return redirect('communication:announcement_detail', announcement_id=announcement.id)

    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, user=request.user, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, "Announcement updated successfully.")
            return redirect('communication:announcement_detail', announcement_id=announcement.id)
    else:
        form = AnnouncementForm(user=request.user, instance=announcement)

    return render(request, 'communication/announcement_form.html', {
        'form': form,
        'announcement': announcement,
        'title': 'Edit Announcement'
    })

@login_required
@require_POST
def announcement_delete(request, announcement_id):
    """Delete an announcement"""
    announcement = get_object_or_404(Announcement, id=announcement_id)

    # Check if user is the creator
    if announcement.created_by != request.user:
        messages.error(request, "You don't have permission to delete this announcement.")
        return redirect('communication:announcement_detail', announcement_id=announcement.id)

    title = announcement.title
    announcement.delete()

    messages.success(request, f"Announcement '{title}' deleted successfully.")
    return redirect('communication:announcements_list')

@login_required
@require_POST
def announcement_publish(request, announcement_id):
    """Publish an unpublished announcement"""
    announcement = get_object_or_404(Announcement, id=announcement_id)

    # Check if user is the creator
    if announcement.created_by != request.user:
        messages.error(request, "You don't have permission to publish this announcement.")
        return redirect('communication:announcement_detail', announcement_id=announcement.id)

    # Check if already published
    if announcement.is_published:
        messages.warning(request, "This announcement is already published.")
        return redirect('communication:announcement_detail', announcement_id=announcement.id)

    # Publish the announcement
    announcement.is_published = True
    announcement.publish_at = timezone.now()
    announcement.save()

    # Log the publication
    log_communication_activity(
        'ANNOUNCEMENT_PUBLISHED',
        request.user,
        f"Published announcement: {announcement.title}",
        announcement=announcement
    )

    messages.success(request, "Announcement published successfully.")
    return redirect('communication:announcement_detail', announcement_id=announcement.id)

@login_required
@require_POST
def announcement_mark_read(request, announcement_id):
    """Mark an announcement as read"""
    announcement = get_object_or_404(Announcement, id=announcement_id)

    # Create read record if not exists
    AnnouncementRead.objects.get_or_create(
        announcement=announcement,
        user=request.user
    )

    # For AJAX requests
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})

    return redirect('communication:announcements_list')

# External Integration Views
@login_required
def integrations_list(request):
    """List all external integrations"""
    # Check if user has admin access
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access external integrations.")
        return redirect('dashboard:index')

    integrations = ExternalIntegration.objects.all().order_by('name')

    return render(request, 'communication/integrations_list.html', {
        'integrations': integrations
    })

@login_required
def integration_create(request):
    """Create a new external integration"""
    # Check if user has admin access
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to create external integrations.")
        return redirect('communication:integrations_list')

    if request.method == 'POST':
        form = ExternalIntegrationForm(request.POST)
        if form.is_valid():
            integration = form.save(commit=False)
            integration.created_by = request.user
            integration.save()

            # Log the creation
            log_communication_activity(
                'EXTERNAL_SYNC',
                request.user,
                f"Created new {integration.get_platform_type_display()} integration: {integration.name}",
                metadata={'integration_id': integration.id, 'platform_type': integration.platform_type}
            )

            messages.success(request, f"{integration.get_platform_type_display()} integration created successfully.")
            return redirect('communication:integration_detail', integration_id=integration.id)
    else:
        form = ExternalIntegrationForm()

    return render(request, 'communication/integration_form.html', {
        'form': form,
        'title': 'Create External Integration'
    })

@login_required
def integration_detail(request, integration_id):
    """Display details of an external integration"""
    # Check if user has admin access
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to view external integration details.")
        return redirect('dashboard:index')

    integration = get_object_or_404(ExternalIntegration, id=integration_id)

    # Get recent messages from this integration
    recent_messages = ExternalMessage.objects.filter(integration=integration).order_by('-received_at')[:20]

    return render(request, 'communication/integration_detail.html', {
        'integration': integration,
        'recent_messages': recent_messages
    })

@login_required
def integration_edit(request, integration_id):
    """Edit an existing external integration"""
    # Check if user has admin access
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to edit external integrations.")
        return redirect('communication:integrations_list')

    integration = get_object_or_404(ExternalIntegration, id=integration_id)

    if request.method == 'POST':
        form = ExternalIntegrationForm(request.POST, instance=integration)
        if form.is_valid():
            form.save()

            # Log the update
            log_communication_activity(
                'EXTERNAL_SYNC',
                request.user,
                f"Updated {integration.get_platform_type_display()} integration: {integration.name}",
                metadata={'integration_id': integration.id, 'platform_type': integration.platform_type}
            )

            messages.success(request, "Integration updated successfully.")
            return redirect('communication:integration_detail', integration_id=integration.id)
    else:
        form = ExternalIntegrationForm(instance=integration)

    return render(request, 'communication/integration_form.html', {
        'form': form,
        'integration': integration,
        'title': 'Edit External Integration'
    })

@login_required
@require_POST
def integration_toggle_active(request, integration_id):
    """Toggle the active status of an integration"""
    # Check if user has admin access
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to modify external integrations.")
        return redirect('communication:integrations_list')

    integration = get_object_or_404(ExternalIntegration, id=integration_id)

    # Toggle active status
    integration.is_active = not integration.is_active
    integration.save()

    status = "activated" if integration.is_active else "deactivated"

    # Log the status change
    log_communication_activity(
        'EXTERNAL_SYNC',
        request.user,
        f"{integration.get_platform_type_display()} integration {status}: {integration.name}",
        metadata={'integration_id': integration.id, 'platform_type': integration.platform_type, 'action': status}
    )

    messages.success(request, f"Integration {status} successfully.")
    return redirect('communication:integration_detail', integration_id=integration.id)

@login_required
@require_POST
def integration_sync(request, integration_id):
    """Manually trigger a sync with an external integration"""
    # Check if user has admin access
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to sync external integrations.")
        return redirect('communication:integrations_list')

    integration = get_object_or_404(ExternalIntegration, id=integration_id)

    # Check if integration is active
    if not integration.is_active:
        messages.error(request, "Cannot sync inactive integration. Please activate it first.")
        return redirect('communication:integration_detail', integration_id=integration.id)

    # Update last sync time
    integration.last_sync = timezone.now()
    integration.save()

    # Log the sync attempt
    log_communication_activity(
        'EXTERNAL_SYNC',
        request.user,
        f"Manually synced {integration.get_platform_type_display()} integration: {integration.name}",
        metadata={'integration_id': integration.id, 'platform_type': integration.platform_type}
    )

    # Here you would actually implement the sync logic based on the platform type
    # This is a placeholder for now
    messages.success(request, f"Sync with {integration.get_platform_type_display()} initiated successfully.")
    return redirect('communication:integration_detail', integration_id=integration.id)

# Message Template Views
@login_required
def templates_list(request):
    """List all message templates"""
    # Get templates (staff can see all, regular users see only active ones)
    if request.user.is_staff:
        templates = MessageTemplate.objects.all()
    else:
        templates = MessageTemplate.objects.filter(is_active=True)

    # Filter by type if requested
    template_type = request.GET.get('type')
    if template_type:
        templates = templates.filter(template_type=template_type)

    # Order by name
    templates = templates.order_by('name')

    # Get template types for filtering
    template_types = dict(MessageTemplate.TEMPLATE_TYPES)

    return render(request, 'communication/templates_list.html', {
        'templates': templates,
        'template_types': template_types,
        'selected_type': template_type
    })

@login_required
def template_create(request):
    """Create a new message template"""
    # Check if user has permission to create templates
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to create message templates.")
        return redirect('communication:templates_list')

    if request.method == 'POST':
        form = MessageTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()

            # Log the creation
            log_communication_activity(
                'TEMPLATE_USED',
                request.user,
                f"Created new {template.get_template_type_display()} template: {template.name}",
                metadata={'template_id': template.id, 'template_type': template.template_type}
            )

            messages.success(request, "Message template created successfully.")
            return redirect('communication:template_detail', template_id=template.id)
    else:
        form = MessageTemplateForm()

    return render(request, 'communication/template_form.html', {
        'form': form,
        'title': 'Create Message Template'
    })

@login_required
def template_detail(request, template_id):
    """Display a single message template"""
    template = get_object_or_404(MessageTemplate, id=template_id)

    # Regular users can only view active templates
    if not request.user.is_staff and not template.is_active:
        messages.error(request, "This message template is not available.")
        return redirect('communication:templates_list')

    # Check if user has edit permission
    can_edit = request.user.is_staff or template.created_by == request.user

    return render(request, 'communication/template_detail.html', {
        'template': template,
        'can_edit': can_edit
    })

@login_required
def template_edit(request, template_id):
    """Edit an existing message template"""
    template = get_object_or_404(MessageTemplate, id=template_id)

    # Check if user has permission to edit
    if not request.user.is_staff and template.created_by != request.user:
        messages.error(request, "You don't have permission to edit this template.")
        return redirect('communication:template_detail', template_id=template.id)

    if request.method == 'POST':
        form = MessageTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()

            # Log the update
            log_communication_activity(
                'TEMPLATE_USED',
                request.user,
                f"Updated {template.get_template_type_display()} template: {template.name}",
                metadata={'template_id': template.id, 'template_type': template.template_type}
            )

            messages.success(request, "Message template updated successfully.")
            return redirect('communication:template_detail', template_id=template.id)
    else:
        form = MessageTemplateForm(instance=template)

    return render(request, 'communication/template_form.html', {
        'form': form,
        'template': template,
        'title': 'Edit Message Template'
    })

@login_required
@require_POST
def template_delete(request, template_id):
    """Delete a message template"""
    template = get_object_or_404(MessageTemplate, id=template_id)

    # Check if user has permission to delete
    if not request.user.is_staff and template.created_by != request.user:
        messages.error(request, "You don't have permission to delete this template.")
        return redirect('communication:template_detail', template_id=template.id)

    name = template.name
    template.delete()

    # Log the deletion
    log_communication_activity(
        'TEMPLATE_USED',
        request.user,
        f"Deleted message template: {name}",
        metadata={'template_type': template.template_type}
    )

    messages.success(request, f"Message template '{name}' deleted successfully.")
    return redirect('communication:templates_list')

# API endpoints for HTMX
@login_required
def api_unread_counts(request):
    """API endpoint to get unread counts for chat rooms and announcements"""
    user = request.user

    # Get unread chat message counts
    unread_chats = ChatRoomMembership.objects.filter(user=user).select_related('room')
    chat_counts = {}

    for membership in unread_chats:
        if membership.last_read_at:
            count = Message.objects.filter(
                room=membership.room,
                created_at__gt=membership.last_read_at
            ).count()
        else:
            count = Message.objects.filter(room=membership.room).count()

        chat_counts[str(membership.room.id)] = count

    # Get unread announcement count
    announcements = Announcement.objects.filter(
        Q(target_all_users=True) |
        Q(target_users=user) |
        Q(target_departments=user.userprofile.department)
    ).distinct()

    read_announcements = AnnouncementRead.objects.filter(
        user=user,
        announcement__in=announcements
    ).values_list('announcement_id', flat=True)

    unread_announcements_count = announcements.exclude(id__in=read_announcements).count()

    return JsonResponse({
        'chat_counts': chat_counts,
        'total_unread_chats': sum(chat_counts.values()),
        'unread_announcements': unread_announcements_count,
        'total_unread': sum(chat_counts.values()) + unread_announcements_count
    })

@login_required
@require_POST
def api_mark_as_read(request, room_id):
    """API endpoint to mark all messages in a room as read"""
    room = get_object_or_404(ChatRoom, id=room_id)

    # Check if user can access this room
    if not user_can_access_room(request.user, room):
        return JsonResponse({'error': "You don't have access to this chat room."}, status=403)

    # Update the user's membership
    try:
        membership = ChatRoomMembership.objects.get(room=room, user=request.user)
        membership.last_read_at = timezone.now()
        membership.save()
    except ChatRoomMembership.DoesNotExist:
        # Create membership if it doesn't exist
        ChatRoomMembership.objects.create(
            room=room,
            user=request.user,
            role='MEMBER',
            last_read_at=timezone.now()
        )

    return JsonResponse({'status': 'success'})