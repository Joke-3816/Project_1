from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.templating import Jinja2Templates
from schemas import PostCreate,PostResponse, UserResponse, UserCreate, PostUpdate
from sqlalchemy import select 
from sqlalchemy.orm import Session
import models
from database import Base, engine, get_db
from typing import Annotated

Base.metadata.create_all(bind=engine)


app=FastAPI()



templates = Jinja2Templates(directory="templates")

@app.get("/", include_in_schema=False)
@app.get("/posts", include_in_schema=False)
def home(request:Request, db: Annotated[Session,Depends(get_db)]):
    result=db.execute(select(models.Post))
    posts=result.scalars().all()
    return templates.TemplateResponse(request,"home.html",{"posts": posts,"title":"Home"})

@app.post("/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED,)
def create_user(user: UserCreate, db: Annotated[Session,Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.username == user.username),)
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail = "Username already exists",)
    result2 = db.execute(select(models.User).where(models.User.email == user.email),)
    existing_email = result2.scalars().first()
    
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail = "Username already exists",)
    new_user = models.User(
        username=user.username,
        email=user.email,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user



@app.get("/api/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Annotated[Session,Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == user_id),)
    user = result.scalars().first()

    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "User not found")

@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
def get_user_posts(user_id:int, db: Annotated[Session,Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == user_id),)
    user= result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User was not found")
    result1 = db.execute(select(models.Post).where(models.Post.user_id == user_id),)
    posts = result1.scalars().all()
    return posts


@app.get("/api/posts", response_model = list[PostResponse])
def get_posts(db: Annotated[Session,Depends(get_db)]):
    result = db.execute(select(models.Post))
    posts = result.scalars().all()
    return posts



@app.post("/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED,)
def create_post(post: PostCreate, db:Annotated[Session,Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == post.user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    new_post=models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,

    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


@app.get("posts/{post_id}",include_in_schema=False)
def get_post(request: Request, post_id: int, db:Annotated[Session,Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id),)
    post = result.scalars().first()
    title = post.title
    author = post.author
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse(request,"posts.html",{"author": author,"post": post,"title": title })


@app.put("/api/posts/{post_id}",response_model=PostResponse)
def update_post_full(post_id: int, post_data: PostCreate, db:Annotated[Session,Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id),)
    post = result.scalars().first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post_data.user_id != post.user_id:
        result1 = db.execute(select(models.User).where(models.User.id == post.user_id))
        user = result1.scalars().first()
        if not user:
            raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )
    post.title=post_data.title
    post.content=post_data.content
    post.user_id=post_data.user_id

    db.commit()
    db.refresh(post)
    return post


@app.patch("/api/posts/{post_id}",response_model=PostResponse)
def update_post_partial(post_id: int, post_data: PostUpdate, db:Annotated[Session,Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id),)
    post = result.scalars().first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post,field,value)
    db.commit()
    db.refresh(post)
    return post


@app.delete("/api/posts/{post_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Annotated[Session,Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id),)
    post = result.scalars().first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(post)
    db.commit()