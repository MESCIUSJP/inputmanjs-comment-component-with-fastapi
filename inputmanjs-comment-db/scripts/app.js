document.addEventListener('DOMContentLoaded', () => {

    const gcComment = new GC.InputMan.GcComment(document.getElementById('gcComment'), {
        dataSource: {
            enabled: true,
            remote: {
                comments: {
                    read: {
                        url: `http://localhost:8000/comments`,
                    },
                    create: {
                        url: `http://localhost:8000/comments`,
                    },
                    update: {
                        url: `http://localhost:8000/comments`,
                    },
                    delete: {
                        url: `http://localhost:8000/comments`,
                    }
                },
                users: {
                    read: {
                        url: `http://localhost:8000/users`,
                        schema: {
                            dataSchema: {
                                name: 'username'
                            }
                        }
                    }
                },
                reactions: {
                    read: {
                        url: `http://localhost:8000/reactions`,
                    },
                    create: {
                        url: `http://localhost:8000/reactions`,
                    },
                    delete: {
                        url: `http://localhost:8000/reactions`,
                    }
                },
            }
        },
        editorConfig: {
            height: 150,
        },
        commentMode: GC.InputMan.GcCommentMode.ThreadMode,
        userInfo: {
            id: "1",
            username: "森上 偉久馬",
            avatar: 'img/avatar1.png',
            avatarType: 'square',
        }
    });
});