$(document).ready(function() {
  window.userId_ = {{ user_id }};
  window.chatId_ = undefined;
  window.chats_ = {}

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

  function setChatsHtml(chats) {
    let html = "";
    for (chat of chats) {
      let activeHtml = 
        chat.chat_id == window.chatId_ ? "active text-white" : "";
      console.log(chat.chat_id)
      console.log(window.chatId_)
      console.log(activeHtml)
      html += `{% include "chat.html" %}`;
    }
    $(".chats-box").html(html);
  }

  function fetchChats(userId) {
    return $.get(`/chats?user_id=${userId}`, {})
      .done(response => {
        for (chat of response.chats) {
          window.chats_[chat.chat_id] = chat;
        }
      });
  }

  function setMessagesHtml(messages) {
    let html = "";
    for (message of messages) {
      if (message.user.user_id === window.userId_) {
        html += `{% include "message_sent.html" %}`
      } else {
        html += `{% include "message_received.html" %}`
      }
    }
    $(".messages-box .list-group").html(html);
    $(".messages-box").scrollTop($(".messages-box .list-group")[0].scrollHeight);
  } 

  function pollServer() {
    $.ajax({
      url: `/message-stream?user_id=${window.userId_}`,
      success: response => {
        message = response.message
        if (!!message) {
          chat = window.chats_[message.chat_id];
          chat.messages.push(message);
          if (chat.chat_id == window.chatId_) {
            setMessagesHtml(chat.messages);
            setChatsHtml(Object.values(window.chats_));
          }
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
        message = response.message;
        chat = window.chats_[message.chat_id];
        chat.messages.push(message);
        if (chat.chat_id == window.chatId_) {
          setMessagesHtml(chat.messages);
          setChatsHtml(Object.values(window.chats_));
        }
    });
    $("#send-input").val("");
  });

  fetchChats(window.userId_)
    .done(response => {
      window.chatId_ = window.chatId_ || response.chats[0].chat_id;
      for (chat of response.chats) {
        if (chat.chat_id == window.chatId_) {
          setMessagesHtml(chat.messages);
          return 
        }
      }
    })
    .done(unusedResponse => {
        setChatsHtml(Object.values(window.chats_));
    });

  pollServer();
});
