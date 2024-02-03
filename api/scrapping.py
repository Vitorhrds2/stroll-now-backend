import instaloader

def baixar_posts(profile):
    bot = instaloader.Instaloader()
    profile = instaloader.Profile.from_username(bot.context, profile)
    posts = profile.get_posts()
    numero_de_posts_desejado = 1
    posts_baixados = 0

    for index, post in enumerate(posts, 1):
        if posts_baixados >= numero_de_posts_desejado:
            break

        posts_baixados += 1
        return post.url

def pegarBio(profile):
    bot = instaloader.Instaloader()
    profile = instaloader.Profile.from_username(bot.context, profile)
    return profile.biography