mod database;

use crate::database::{DatabaseQueries, UserModel};
use crate::database::{CollectibleModel, DatabaseHelper, };
use anyhow::{bail, Error};
use anyhow::Result;
use serde_derive::Deserialize;
use serenity::client::{Context, EventHandler};
use serenity::model::channel::{Attachment, Message, Reaction};
use serenity::model::id::UserId;
use serenity::utils::{MessageBuilder};
use serenity::{async_trait, Client};
use std::sync::Arc;
use tokio::fs;
use hex_literal::hex;
use serenity::framework::StandardFramework;
use image::ImageOutputFormat;
use serenity::model::prelude::Ready;
use std::fmt::Write;
use rand::Rng;
use serenity::model::user::User;
use warp::Filter;
use serde_derive::Serialize;

macro_rules! none_error {
    ($x:expr) => {{
        match $x {
            Some(x) => x,
            None => bail!("none error"),
        }
    }};
}

fn get_image_extension(image: &[u8]) -> &str {
    const PNG_MAGIC: &[u8] = &hex!("89 50 4E 47 0D 0A 1A 0A");
    const JPG_MAGIC1: &[u8] = &hex!("FF D8 FF EE");
    const JPG_MAGIC2: &[u8] = &hex!("FF D8 FF E0 00 10 4A 46 49 46 00 01");
    const JPG_MAGIC3: &[u8] = &hex!("FF D8 FF E1");

    if image.starts_with(PNG_MAGIC) {
        "png"
    } else if image.starts_with(JPG_MAGIC1) || image.starts_with(JPG_MAGIC2) || image.starts_with(JPG_MAGIC3) {
        "jpg"
    } else {
        "unknown"
    }
}

async fn send_message(message: &str, context: &Context, original: &Message, image: Option<&[u8]>) -> Result<()> {
    let message: String = message.chars().take(2000).collect();
    original
        .channel_id
        .send_message(context, |builder| {
            builder.content(message);
            if let Some(image) = image {
                let image_name = format!("image.{}", get_image_extension(image));
                builder.add_file((image, image_name.as_str()));
            }
            builder
        })
        .await?;

    Ok(())
}

struct DiscordBot {
    config: Configuration,
    database_helper: DatabaseHelper,
}

impl DiscordBot {
    async fn new(config: Configuration) -> Result<(Arc<DiscordBot>, Client)> {
        let database_helper = DatabaseHelper {
            connection_string: config.database_connection_string.clone(),
        };
        let bot = Arc::new(DiscordBot {
            config,
            database_helper,
        });

        let discord = DiscordHandler { bot: bot.clone() };
        let client = Client::new(&bot.config.discord_token).event_handler(discord).framework(StandardFramework::new()).await?;

        bot.database_helper.simple().await?.run_create_tables().await?;

        Ok((bot, client))
    }
}

struct DiscordHandler {
    bot: Arc<DiscordBot>,
}

impl DiscordHandler {
    async fn do_command(&self, string: &[&str], context: &Context, message: &Message) -> Result<()> {
        let command = string[0];
        let args = &string[1..];

        if command == "hello" {
            self.on_hello(context, message).await?;
        } else if command == "ping" {
            let who = none_error!(string.get(1));
            self.ping_someone(context, message, who).await?;
        } else if command == "clear" {
            self.clear_channel(context, message).await?;
        } else if command == "add_collectible" {
            self.on_create_collectible(context, message, args).await?;
        } else if command == "my_collectibles" {
            self.on_my_collectible(context, message).await?;
        } else if command == "add_pack" {
            self.on_add_pack(context, message, args).await?;
        } else if command == "packs" {
            self.on_packs(context, message).await?;
        } else if command == "open" {
            self.on_open(context, message, args).await?;
        } else if command == "userinfo" {
            self.on_user_info(context, message).await?;
        }

        Ok(())
    }

    async fn on_add_pack(&self, _context: &Context, original: &Message, args: &[&str]) -> Result<()> {
        let name = none_error!(args.get(0));
        let price = none_error!(args.get(1)).parse()?;

        let ids: Result<Vec<i32>, std::num::ParseIntError> =
            args[2..].iter().map(|x| x.parse()).collect();
        let ids = ids?;
        let photo: Option<Vec<u8>> = DiscordHandler::get_image(&original).await?;

        let mut database = self.bot.database_helper.simple().await?;
        let database = database.transaction().await?;
        let user = database
            .get_user_by_discord_id(original.author.id.0)
            .await?;

        for i in &ids {
            let _ = database.get_collectibles_by_id(*i).await?;
        }

        let guild_id = original.guild_id.unwrap().0 as i64;
        database.add_pack(name, &ids, user.id, guild_id, photo.as_deref(), price).await?;

        database.commit().await?;

        Ok(())
    }

    async fn on_open(&self, context: &Context, original: &Message, args: &[&str]) -> Result<()> {
        let name = none_error!(args.get(0));
        let guild_id = none_error!(original.guild_id).0;

        let database = self.bot.database_helper.simple().await?;
        let pack = database.get_pack_by_guild_name(name, guild_id as i64).await?;
        let collectibles = &pack.collectibles;
        if collectibles.is_empty() {
            return Err(Error::msg("no collectibles"));
        }

        let user = database.get_user_by_discord_id(original.author.id.0).await?;
        if user.money < pack.price {
            original.reply(context, "🧐 you don't have enough money 🧐").await?;
            return Ok(());
        }

        self.add_money(&original.author, -(pack.price as i32)).await?;

        let index = rand::thread_rng().gen_range(0, collectibles.len());
        let chosen = &collectibles[index];

        let message = format!("you opened {}! yay! 🙀🙀🙀 you paid {} jerrygold", chosen.name, pack.price);
        send_message(&message, context, original, chosen.photo.as_deref()).await?;

        database.add_collectible_for_user(user.id, chosen.id).await?;

        Ok(())
    }

    async fn on_packs(&self, context: &Context, original: &Message) -> Result<()> {
        let guild: i64 = none_error!(original.guild_id).0 as i64;

        let database = self.bot.database_helper.simple().await?;
        let packs = database.get_packs_for_guild(guild).await?;

        let mut string = String::new();
        for (index, (name, count)) in packs.into_iter().enumerate() {
            writeln!(&mut string, "{}. {}, count={}", index + 1, name, count)?;
        }

        original.reply(context, string).await?;

        Ok(())
    }

    async fn on_my_collectible(&self, context: &Context, original: &Message) -> Result<()> {
        let mut database = self.bot.database_helper.simple().await?;
        let database = database.transaction().await?;

        let user = database
            .get_user_by_discord_id(original.author.id.0)
            .await?;
        let collectibles: Vec<CollectibleModel> =
            database.get_collectibles_for_user_id(user.id).await?;

        for i in collectibles {
            let text = format!(
                "name={}, description={}, rarity={}, id={}, created_by=",
                i.name, i.description, i.rarity, i.id
            );

            let message = MessageBuilder::new()
                .push(text)
                .user(i.created_by.discord_id as u64)
                .build();

            send_message(&message, &context, &original, i.photo.as_deref()).await?;
        }

        Ok(())
    }

    async fn update_user(&self, id: u64, message: &Message) -> Result<()> {
        let mut client = self.bot.database_helper.simple().await?;
        client.update_info(id, &message.author.name).await?;

        self.add_money(&message.author, message.content.trim().len() as i32).await?;

        Ok(())
    }

    async fn on_create_collectible(
        &self,
        _context: &Context,
        original: &Message,
        args: &[&str],
    ) -> Result<()> {
        let name: &str = none_error!(args.get(0));
        let rarity: &str = none_error!(args.get(1));
        let photo: Option<Vec<u8>> = DiscordHandler::get_image(&original).await?;

        let mut database = self.bot.database_helper.simple().await?;
        let database = database.transaction().await?;

        let user = database
            .get_user_by_discord_id(original.author.id.0)
            .await?;

        let collectible = CollectibleModel {
            id: 0,
            name: name.to_string(),
            description: "".to_string(),
            rarity: rarity.to_string(),
            photo,
            // created: 0,
            created_by: user,
            created_on_server: original.guild_id.unwrap().0 as i64,
        };

        database.insert_collectible(collectible).await?;

        database.commit().await?;

        Ok(())
    }

    async fn get_image(message: &Message) -> Result<Option<Vec<u8>>> {
        let attachment = match DiscordHandler::get_image_option(message) {
            Some(x) => x,
            None => return Ok(None),
        };

        let mut result = attachment.download().await?;
        let image = image::load_from_memory(&result)?;
        let image = image.thumbnail(100, 100);

        result.clear();
        image.write_to(&mut result, ImageOutputFormat::Png)?;

        Ok(Some(result))
    }

    fn get_image_option(message: &Message) -> Option<&Attachment> {
        let attachment = message.attachments.get(0)?;
        attachment.width?;
        Some(attachment)
    }

    async fn on_hello(&self, context: &Context, original: &Message) -> Result<()> {
        let message = MessageBuilder::new()
            .push("hello, ")
            .mention(&original.author)
            .build();
        original.channel_id.say(&context, message).await?;
        Ok(())
    }

    async fn ping_someone(&self, context: &Context, original: &Message, who: &str) -> Result<()> {
        let who = who.parse()?;
        let message = MessageBuilder::new()
            .push("boo, ")
            .mention(&UserId(who))
            .build();
        original.channel_id.say(&context, message).await?;

        Ok(())
    }

    async fn on_user_info(&self, context: &Context, original: &Message) -> Result<()> {
        let database = self.bot.database_helper.simple().await?;
        let user = database.get_user_by_discord_id(original.author.id.0).await?;

        let message = format!("name={}, money={}", original.author.name, user.money);
        original.reply(context, message).await?;

        Ok(())
    }

    async fn clear_channel(&self, context: &Context, original: &Message) -> Result<()> {
        loop {
            let messages = original
                .channel_id
                .messages(&context, |retriever| {
                    retriever.before(original.id).limit(10)
                })
                .await?;

            if messages.is_empty() {
                break;
            }

            for i in messages {
                i.delete(context).await?;
            }
        }

        Ok(())
    }

    async fn add_money(&self, user: &User, money: i32) -> Result<()> {
        println!("adding {} money to {}", money, user.name);
        let database = self.bot.database_helper.simple().await?;
        database.add_money(user.id.0, money).await?;
        Ok(())
    }
}

fn split_command(string: &str) -> Vec<&str> {
    string.split(' ').collect()
}

#[async_trait]
impl EventHandler for DiscordHandler {
    async fn message(&self, context: Context, message: Message) {
        println!("{}: {}", message.author.name, message.content);
        if message.author.bot {
            return;
        }

        self
            .update_user(message.author.id.0, &message)
            .await.unwrap();

        let text = message.content.trim().to_string();
        if text.starts_with('~') {
            let command = split_command(&text[1..]);
            let emoticon = match self.do_command(&command, &context, &message).await {
                Ok(_) => '✅',
                Err(e) => {
                    println!("{:?}", e);
                    '❌'
                }
            };

            message.react(context, emoticon).await.unwrap();
        }
    }

    async fn reaction_add(&self, context: Context, add_reaction: Reaction) {
        self.add_money(&add_reaction.user_id.to_user(&context).await.unwrap(), 50).await.unwrap();
    }

    async fn ready(&self, _ctx: Context, _data_about_bot: Ready) {
        println!("Ready!");
    }
}

#[derive(Deserialize)]
struct Configuration {
    discord_token: String,
    database_connection_string: String,
}

async fn read_config() -> Result<Configuration> {
    let text = fs::read_to_string("config.toml").await?;
    let config = toml::from_str(&text)?;
    Ok(config)
}

macro_rules! anyhow_to_warp {
    ($x:expr) => {{
        match $x {
            Ok(x) => x,
            Err(e) => {
                println!("{:?}", e);
                return Err(warp::reject::not_found());
            }
        }
    }};
}

#[derive(Serialize)]
struct UserInfoResponse {
    user: UserModel,
    collectibles: Vec<CollectibleModel>
}

async fn http_on_user_id(bot: Arc<DiscordBot>, id: u64) -> Result<Box<dyn warp::Reply>, warp::Rejection>{
    let database: tokio_postgres::Client = anyhow_to_warp!(bot.database_helper.simple().await);
    let user: UserModel = anyhow_to_warp!(database.get_user_by_discord_id(id).await);
    let collectibles = anyhow_to_warp!(database.get_owned_collectibles_for_user(user.id).await);

    let result = UserInfoResponse {
        user,
        collectibles
    };

    let result = serde_json::to_string_pretty(&result).unwrap();

    Ok(Box::new(result))
}

async fn warp_server(bot: Arc<DiscordBot>) -> Result<()> {
    let user = warp::path!("user" / u64)
        .and_then(move |user_id| http_on_user_id(bot.clone(), user_id));

    warp::serve(user)
        .run(([0, 0, 0, 0], 3421))
        .await;

    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    let config = read_config().await?;

    let (bot, mut client) = DiscordBot::new(config).await?;
    tokio::spawn(async move {
        let result = warp_server(bot).await;
        if let Err(e) = result {
            println!("{:?}", e);
        }
    });

    client.start().await?;



    Ok(())
}
