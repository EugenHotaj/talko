window.userId_ = {{ user_id }};
window.chatId_ = undefined;
window.chats_ = [];
window.messages_ = [];

function timestampToDateTime(timestamp, include_time = true) {
  const dateTime = new Date(timestamp);
  let options = { month: 'long', day: 'numeric'};
  if (include_time) {
    options.hour = 'numeric';
    options.minute = 'numeric';
  }
  return dateTime.toLocaleDateString('us-ES', options)
}

function getUserAvatarText(userName) {
  text = "" 
  for (split of userName.split(" ")) {
    text += split[0]
  }
  return text
}

function getChatAvatarText(chat, userId) {
  if (chat.users.length > 2) {
    return `+${chat.users.length - 1}`;
  }
  for (user of chat.users) {
    if (user.user_id != window.userId_) {
      return getUserAvatarText(user.user_name);
    }
  }
}

function getChats(userId) {
  return $.get(`/chats?user_id=${userId}`, {})
    .done(response => { 
      // TODO(eugenhotaj): We need more robust checking here, e.g.
      // that all the chat_ids are the same.
      if (response.chats.length == window.chats_.length) {
        return
      }

      window.chats_ = response.chats
      let html = "";
      for (chat of window.chats_) {
        html += `{% include "chat.html" %}`
      }
      $(".chats-box").html(html);
    });
}

function setMessagesHtml(messages) {
  // TODO(eugenhotaj): We need more robust checking here, e.g.
  // that all the message_ids are the same.
  if (messages.length == window.messages_.length) {
    return
  }

  window.messages_ = messages
  let html = "";
  for (message of window.messages_) {
    if (message.user.user_id === window.userId_) {
      html += `{% include "message_sent.html" %}`
    } else {
      html += `{% include "message_received.html" %}`
    }
  }
  $(".messages-box .list-group").html(html);
  $(".messages-box").scrollTop($(".messages-box .list-group")[0].scrollHeight);
} 

function getMessages(userId, chatId) {
  return $.get(`/messages?user_id=${userId}&chat_id=${chat_id}`, {})
          .done(response => { setMessagesHtml(response.messages); });
}

function pollServer() {
  $.ajax({
    url: `/message-stream?user_id=${window.userId_}`,
    success: response => {
      if (!!response.message) {
        // TODO(eugenhotaj): This is a pretty inefficient and roundabout
        // way to update the messages.
        messages = window.messages_.concat([response.message]);
        setMessagesHtml(messages);
      }
    },
    complete: pollServer, 
    timeout: 30000,
  });
}

// TODO(eugenhotaj): We need to attach listners to the chats list so the
// user can switch to other chats.
// Attach listener.
$("#send-message").submit((element) => {
  element.preventDefault();
  let messageText = $("#send-input").val();
  let data = {chat_id: window.chatId_, user_id: window.userId_, message_text: messageText};
  $.ajax({
    url: "/messages",
    method: "POST",
    contentType: "application/json; charset=UTF-8",
    data: JSON.stringify(data),
    dataType: "json",
  }).done(response => { 
    // TODO(eugenhotaj): This is a pretty inefficient and roundabout
    // way to update the messages.
    messages = window.messages_.concat([response.message]);
    setMessagesHtml(messages);
  });
  $("#send-input").val("");
});

