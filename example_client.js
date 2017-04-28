// example based on work assignment given by https://github.com/eidheim
class Chat {
  constructor(context) {
    this.context=context;
    this.text = "";

    this.ws = new WebSocket("ws://localhost:8080");

    this.ws.onerror = (error) => {
      $("#connection_label").html("Not connected");
    };

    this.ws.onopen = () => {
      $("#connection_label").html("Connected");
    };

    this.ws.onmessage = (event) => {
      var json=JSON.parse(event.data);

      if(json.text) {
        this.add_text(json.text.content);
      }
    };

    this.ws.onclose = function(message) {
      $("#connection_label").html("Not connected");
    };
  }

  add_text(t) {
    this.text = t + "\n" + this.text;
    $('#chat').html(this.text);
  };

  on_text_submit(s) {
    if ($('#chatcontent').val() === "") {
      return false;
    }
    if(this.ws.readyState==1) {
      var json={"text": { "content": s}};

      this.ws.send(JSON.stringify(json));
    }
  }
}

var chat;
$(document).ready(function(){
  chat = new Chat($('#chat'));

  $( "#submitchat" ).click(function() {
    var name = $('#chatname').val();
    if (name=== "") {
      name = "Anonymous";
    }
    var content = $('#chatcontent').val();
    var color = $('#chatcolor').val();
    var dt = new Date();
    var time = "[" + dt.getHours() + ":" + dt.getMinutes() + "]";
    chat.on_text_submit("<div style='color:" + color + "'>" + time + name + ": " + content + "<div>");
    $('#chatcontent').val("");
  });

  $( "#closechat" ).click(function() {
    chat.ws.close();
  });
});
