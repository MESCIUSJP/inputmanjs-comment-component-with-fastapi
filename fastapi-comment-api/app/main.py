from fastapi import Depends, FastAPI, Form, HTTPException, status, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from datetime import datetime
from typing import Union
from .database import engine, get_db
from . import models, schemas

models.Base.metadata.create_all(bind=engine)

# コメント情報取得のヘルパー関数
def get_comment(id: int, db_session: Session):
    return db_session.query(models.Comment).filter(models.Comment.id == id).first()

# ピン留めされたコメント情報取得のヘルパー関数
def get_sticked_comment(db_session: Session):
    return db_session.query(models.Comment).filter(models.Comment.sticked == True).first()

# ユーザー情報取得のヘルパー関数
def get_user(id: int, db_session: Session):
    return db_session.query(models.User).filter(models.User.id == id).first()

app = FastAPI()

# CORS対応
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"] 
)

# Commentを全件取得
@app.get("/comments")
def read_comments(db: Session = Depends(get_db), type : str = Query("NONE")):
    # type=stickの場合はピン留めするコメントの情報を返却
    if type == "sticked":
        sticked_comment = get_sticked_comment(db)
        if sticked_comment is not None:
            return {
                        "id": sticked_comment.id,
                        "parentCommentId": sticked_comment.parentCommentId,
                        "content": sticked_comment.content,
                        "sticked": sticked_comment.sticked,
                        "postTime": sticked_comment.postTime.strftime("%Y/%m/%d %H:%M:%S"),
                        "updateTime": sticked_comment.updateTime.strftime("%Y/%m/%d %H:%M:%S"),
                        "userId": sticked_comment.userId,
                        "mentionInfo": sticked_comment.mentionInfo,
            }
        else:
            return {"hasMore": False, "comments": []}
    else:    
        comments = db.query(models.Comment).all()
        return {
            "hasMore": False,
            "comments": [
                {
                    "id": comment.id,
                    "parentCommentId": comment.parentCommentId,
                    "content": comment.content,
                    "sticked": comment.sticked,
                    "postTime": comment.postTime.strftime("%Y/%m/%d %H:%M:%S"),
                    "updateTime": comment.updateTime.strftime("%Y/%m/%d %H:%M:%S"),
                    "userId": comment.userId,
                    "mentionInfo": comment.mentionInfo,
                }
                for comment in comments
            ],
        }

# Commentを登録
@app.post("/comments")
async def create_comment(
    userId: int = Form(...),
    parentId: Union[int, str, None] = Form(None),
    sticked: bool = Form(False),
    content: str = Form(...),
    mentionInfo: Union[str, None] = Form(None),
    db: Session = Depends(get_db)
):
    formdata = schemas.CommentIn(
        userId=userId,
        parentId=parentId,
        sticked=sticked,
        content=content,
        mentionInfo=mentionInfo,
    )

    comment = models.Comment(
        userId=formdata.userId,
        parentCommentId = None if formdata.parentId == 'undefined' else formdata.parentId,
        sticked=formdata.sticked,
        content=formdata.content,
        mentionInfo=formdata.mentionInfo,
        postTime=datetime.now(),
        updateTime=datetime.now()
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment

# Commentを更新
@app.put("/comments")
async def update_comment(
    id: int = Form(...),
    userId: int = Form(...),
    parentCommentId: Union[int, str, None] = Form(None),
    stick: bool = Form(False),
    content: Union[str, None] = Form(None),
    newContent: Union[str, None] = Form(None),
    mentionInfo: Union[str, None] = Form(None),
    db: Session = Depends(get_db)
):
    formdata = schemas.CommentIn(
        userId=userId,
        parentId=parentCommentId,
        sticked=True if stick is True else False, # ピン留めの状態を更新
        content=newContent if newContent is not None else content,
        mentionInfo=mentionInfo,
    )

    comment = models.Comment(
        userId=formdata.userId,
        parentCommentId=formdata.parentId,
        sticked=formdata.sticked,
        content=formdata.content,
        mentionInfo=formdata.mentionInfo,
        updateTime=datetime.now()
    )
    try:
        sticked_comment = get_sticked_comment(db)
        if sticked_comment is not None and sticked_comment.id != id and comment.sticked:
            # 既にピン留めされているコメントがある場合は、ピン留めを解除
            sticked_comment.sticked = False

        db_comment = get_comment(id,db)
        if db_comment is None:
            raise HTTPException(status_code=404, detail="Comment not found")
        else:
            db_comment.userId = comment.userId
            db_comment.parentCommentId = None if comment.parentCommentId == 'undefined' else comment.parentCommentId
            db_comment.sticked = comment.sticked
            db_comment.content = comment.content
            db_comment.mentionInfo = comment.mentionInfo    
            db_comment.updateTime = comment.updateTime    
    
            db.commit()
            db.refresh(db_comment)
            return db_comment
    except Exception as e:
        db.rollback()  # エラーが発生したらすべての変更をロールバック
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
    finally:
        db.close() 
        
# Commentを削除
@app.delete("/comments")
def delete_comment(commentId: int, db: Session = Depends(get_db)):
    db_comment = get_comment(commentId,db)
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    else:
        db_comment = db.query(models.Comment).filter(models.Comment.id == commentId).delete()
        db.commit()
        return True

# Userを取得
@app.get("/users")
def read_user(id: int, db: Session = Depends(get_db)):
    user = get_user(id, db)
    if user is None:
        return []
    return [user]

# Reactionを取得
@app.get("/reactions")
def read_reaction(commentId: int, userId: int, db: Session = Depends(get_db)):
    reactions = db.query(models.Reaction.reactionChar, func.count(models.Reaction.reactionChar).label("count")
        ).filter(models.Reaction.commentId == commentId).group_by(models.Reaction.reactionChar).all()

    user_reactions = db.query(models.Reaction.reactionChar).filter(models.Reaction.commentId == commentId, models.Reaction.userId == userId).all()
    user_reacted_chars = {reaction[0] for reaction in user_reactions}

    reaction_info = [
        {
            "reactionChar": reaction[0],
            "count": reaction[1],
            "currentUserReacted": reaction[0] in user_reacted_chars
        }
        for reaction in reactions
    ]

    return reaction_info

# Reactionsを登録
@app.post("/reactions")
async def create_reaction(
    reactChar: str = Form(...),
    commentId: int = Form(...),
    userId: int = Form(...),
    db: Session = Depends(get_db)
):
    formdata = schemas.ReactionIn(
        reactionChar=reactChar,
        commentId=commentId,
        userId=userId,
    )

    reaction = models.Reaction(
        reactionChar=formdata.reactionChar,
        commentId=formdata.commentId,
        userId=formdata.userId,
    )

    db.add(reaction)
    db.commit()
    db.refresh(reaction)
    return True

# Reactionを削除
@app.delete("/reactions")
def delete_reaction(commentId: int, userId: int, reactChar: str, db: Session = Depends(get_db)):
    db_reaction = db.query(models.Reaction).filter(models.Reaction.userId == userId, models.Reaction.commentId == commentId, models.Reaction.reactionChar == reactChar).delete()
    if db_reaction == 0:
        raise HTTPException(status_code=404, detail="Reaction not found")
    else:
        db.commit()
        return True

# リクエストエラー時のハンドリング
@app.exception_handler(RequestValidationError)
async def handler(request:Request, exc:RequestValidationError):
    print(exc)
    return JSONResponse(content={}, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
