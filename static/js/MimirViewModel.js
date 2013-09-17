function MimirViewModel(){
    self = this;
    self.files = ko.observableArray();
    self.open_files = ko.observableArray();
    self.file = ko.observable();
    self.filepath = ko.observable("/");
    self.loadFiles = function(item){
        $.getJSON("/+json", function(data){
            for(var i in data.files){
                data.files[i].files = [];
                self.files.push(ko.mapping.fromJS(data.files[i]));
            }
            //self.files(ko.mapping.fromJS(data));
        });
    };
    self.fileClick = function(item){
        history.pushState(null, null, "/"+ item.filepath());
        var fileItem = item;
        self.filepath(item.filepath());
        if(fileItem.files().length > 0) fileItem.files.removeAll();
        else {
            $.getJSON("/"+ item.filepath() +"+json", function(data){
                if(data.mimetype == "directory"){
                   for(var i in data.files){
                        data.files[i].files = [];
                        fileItem.files.push(ko.mapping.fromJS(data.files[i]));
                    }
                } else {
                    exists = false;
                    for(var ii in self.open_files()) if(self.open_files()[ii].filename() == data.filename) exists = true;
                    if (!exists) {
                        self.open_files.push(ko.mapping.fromJS(data));
                    }
                    self.file(data.filename);
                }
            });
        }
    };
    self.tabClick = function(item){
        console.log(item);
        history.pushState(null, null, "/"+ item.filename());
        self.file(item.filename());
    };
    self.loadFiles();
}