use anyhow::{Error, Result};
use postgres_derive::{FromSql, ToSql};
use serenity::async_trait;
use tokio_postgres::{Client, GenericClient, NoTls};
use serde_derive::Serialize;

#[async_trait]
pub trait DatabaseQueries: GenericClient {
    async fn run_create_tables(&mut self) -> Result<()>;
    async fn update_info(&mut self, id: u64, name: &str) -> Result<()>;
    async fn insert_collectible(&self, collectible: CollectibleModel) -> Result<()>;
    async fn get_user_by_discord_id(&self, id: u64) -> Result<UserModel>;
    async fn get_user_by_id(&self, id: i32) -> Result<UserModel>;
    async fn get_collectibles_for_user_id(&self, id: i32) -> Result<Vec<CollectibleModel>>;
    async fn get_collectibles_by_id(&self, id: i32) -> Result<CollectibleModel>;
    async fn add_pack(&self, name: &str, ids: &[i32], user_id: i32, guild_id: i64, photo: Option<&[u8]>, price: i32) -> Result<()>;
    async fn get_packs_for_guild(&self, guild_id: i64) -> Result<Vec<(String, u32)>>;
    async fn get_pack_by_guild_name(&self, name: &str, guild_id: i64) -> Result<PackModel>;
    async fn add_money(&self, user_discord_id: u64, money: i32) -> Result<()>;
    async fn add_collectible_for_user(&self, user_id: i32, collectible_id: i32) -> Result<()>;
    async fn get_owned_collectibles_for_user(&self, user_id: i32) -> Result<Vec<CollectibleModel>>;
}

#[async_trait]
impl<T: GenericClient + Send + Sync> DatabaseQueries for T {
    async fn run_create_tables(&mut self) -> Result<(), Error> {
        const CREATE_TABLES: &str = include_str!("../database/create.sql");

        for i in CREATE_TABLES.split(';') {
            self.query(i, &[]).await?;
        }

        Ok(())
    }

    async fn update_info(&mut self, id: u64, name: &str) -> Result<()> {
        let sql = r#"insert into users (discord_id, last_known_name, first_seen)
        values ($1, $2, now())
        on conflict (discord_id) do update
        set last_known_name = $3"#;

        let id = id as i64;
        self.query(sql, &[&id, &name, &name]).await?;

        Ok(())
    }

    async fn insert_collectible(&self, collectible: CollectibleModel) -> Result<()> {
        let sql = "\
        insert into collectibles (name, description, rarity, photo, created, created_by, created_on_server)\
        values ($1, $2, $3, $4, now(), $5, $6)";

        self.query(
            sql,
            &[
                &collectible.name,
                &collectible.description,
                &collectible.rarity,
                &collectible.photo,
                &collectible.created_by.id,
                &collectible.created_on_server,
            ],
        )
        .await?;

        Ok(())
    }

    async fn get_user_by_discord_id(&self, id: u64) -> Result<UserModel> {
        let id = id as i64;
        let sql = "select * from users where discord_id = $1";
        let row = self.query(sql, &[&id]).await?;
        let row = &row[0];
        let result = UserModel {
            id: row.try_get("id")?,
            discord_id: row.try_get("discord_id")?,
            last_known_name: row.try_get("last_known_name")?,
            money: row.try_get("money")?,
            // first_seen: row.try_get("first_seen")?
        };
        Ok(result)
    }

    async fn get_user_by_id(&self, id: i32) -> Result<UserModel> {
        let id = id as i32;
        let sql = "select * from users where id = $1";
        let row = self.query_one(sql, &[&id]).await?;
        let result = UserModel {
            id: row.try_get("id")?,
            discord_id: row.try_get("discord_id")?,
            last_known_name: row.try_get("last_known_name")?,
            money: row.try_get("money")?
            // first_seen: row.try_get("first_seen")?
        };
        Ok(result)
    }

    async fn get_collectibles_for_user_id(&self, id: i32) -> Result<Vec<CollectibleModel>> {
        let sql = "select * from collectibles where created_by = $1";
        let rows = self.query(sql, &[&id]).await?;

        let mut result = Vec::new();

        for row in rows {
            let created_by: i32 = row.try_get("created_by")?;
            let created_by = self.get_user_by_id(created_by).await?;

            let current = CollectibleModel {
                id: row.try_get("id")?,
                name: row.try_get("name")?,
                description: row.try_get("description")?,
                rarity: row.try_get("rarity")?,
                photo: row.try_get("photo")?,
                // created: 0,
                created_by,
                created_on_server: row.try_get("created_on_server")?,
            };
            result.push(current);
        }

        Ok(result)
    }

    async fn get_collectibles_by_id(&self, id: i32) -> Result<CollectibleModel, Error> {
        let sql = "select * from collectibles where id = $1";
        let row = self.query_one(sql, &[&id]).await?;

        let created_by: i32 = row.try_get("created_by")?;
        let created_by = self.get_user_by_id(created_by).await?;

        let collectible = CollectibleModel {
            id: row.try_get("id")?,
            name: row.try_get("name")?,
            description: row.try_get("description")?,
            rarity: row.try_get("rarity")?,
            photo: row.try_get("photo")?,
            // created: 0,
            created_by,
            created_on_server: row.try_get("created_on_server")?,
        };

        Ok(collectible)
    }

    async fn add_pack(&self, name: &str, ids: &[i32], user_id: i32, guild_id: i64, photo: Option<&[u8]>, price: i32) -> Result<()> {
        let sql = "insert into packs (name, photo, created, created_by, guild_id, price)\
        values ($1, $2, now(), $3, $4, $5)
        returning id";
        let result = self.query_one(sql, &[&name, &photo, &user_id, &guild_id, &price]).await?;
        let pack_id: i32 = result.try_get(0)?;

        for collectible_id in ids {
            let sql = "insert into pack_collectibles (pack_id, collectible_id) values ($1, $2)";
            self.query(sql, &[&pack_id, collectible_id]).await?;
        }

        Ok(())
    }

    async fn get_packs_for_guild(&self, guild_id: i64) -> Result<Vec<(String, u32)>> {
        let sql = "select id, name from packs where guild_id = $1";
        let rows = self.query(sql, &[&guild_id]).await?;

        let mut result = Vec::new();
        for i in rows {
            let pack_id: i32 = i.try_get("id")?;
            let name: String = i.try_get("name")?;

            let sql = "select count(*) from pack_collectibles where pack_id = $1";
            let count = self.query_one(sql, &[&pack_id]).await?;
            let count: i64 = count.try_get(0)?;
            result.push((name, count as u32));
        }

        Ok(result)
    }

    async fn get_pack_by_guild_name(&self, name: &str, guild_id: i64) -> Result<PackModel> {
        let sql = "select * from packs where guild_id = $1 and name = $2";
        let rows = self.query(sql, &[&guild_id, &name]).await?;
        if rows.is_empty() {
            return Err(Error::msg("no pack with that name"));
        }
        let row = &rows[0];
        let id: i32 = row.try_get("id")?;
        let name: String = row.try_get("name")?;
        let price = row.try_get("price")?;

        let sql = "select * from pack_collectibles where pack_id = $1";
        let rows = self.query(sql, &[&id]).await?;

        let mut collectibles = Vec::new();
        for i in rows {
            let collectible_id = i.try_get("collectible_id")?;
            let model = self.get_collectibles_by_id(collectible_id).await?;
            collectibles.push(model);
        }

        Ok(PackModel {
            id,
            name,
            price,
            collectibles
        })
    }

    async fn add_money(&self, user_discord_id: u64, money: i32) -> Result<()> {
        let user_discord_id = user_discord_id as i64;
        let money = money as i32;

        let sql = "update users set money = money + $1 where discord_id = $2";
        self.query(sql, &[&money, &user_discord_id]).await?;

        Ok(())
    }

    async fn add_collectible_for_user(&self, user_id: i32, collectible_id: i32) -> Result<(), Error> {
        let sql = "insert into user_collectibles (user_id, collectible_id) values ($1, $2)";
        self.query(sql, &[&user_id, &collectible_id]).await?;

        Ok(())
    }

    async fn get_owned_collectibles_for_user(&self, user_id: i32) -> Result<Vec<CollectibleModel>> {
        let sql = "select * from user_collectibles where user_id = $1";
        let rows = self.query(sql, &[&user_id]).await?;

        let mut result = Vec::new();
        for i in rows {
            let collectible = self.get_collectibles_by_id(i.try_get("collectible_id")?).await?;
            result.push(collectible);
        }

        Ok(result)
    }
}

pub struct DatabaseHelper {
    pub connection_string: String,
}

#[derive(Debug, ToSql, FromSql, Serialize)]
pub struct UserModel {
    pub id: i32,
    pub discord_id: i64,
    pub last_known_name: String,
    pub money: i32
    // pub first_seen: i64,
}

#[derive(Debug, ToSql, FromSql, Serialize)]
pub struct CollectibleModel {
    pub id: i32,
    pub name: String,
    pub description: String,
    pub rarity: String,
    pub photo: Option<Vec<u8>>,
    // pub created: i64,
    pub created_by: UserModel,
    pub created_on_server: i64,
}

#[derive(Debug, ToSql, FromSql)]
pub struct PackModel {
    pub id: i32,
    pub name: String,
    pub price: i32,
    pub collectibles: Vec<CollectibleModel>
}

impl DatabaseHelper {
    pub async fn simple(&self) -> Result<Client> {
        let client = self.create_client().await?;

        Ok(client)
    }

    async fn create_client(&self) -> Result<Client> {
        let (client, connection) = tokio_postgres::connect(&self.connection_string, NoTls).await?;

        tokio::spawn(async move {
            if let Err(e) = connection.await {
                eprintln!("connection error: {}", e);
            }
        });

        Ok(client)
    }
}
