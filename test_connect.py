import psycopg2

# 数据库连接参数
host = "localhost"  # 或者是数据库服务器的IP地址
database = "postgres"  # 你的数据库名
user = "postgres"  # 你的数据库用户名
password = "164871"  # 你的数据库密码

try:
    # 尝试建立连接
    conn = psycopg2.connect(
        host=host,
        database=database,
        user=user,
        password=password
    )
    # 创建cursor对象
    cur = conn.cursor()
    print("数据库连接成功！")
    # 这里可以执行你的SQL语句
    # 例如，查询数据库版本
    cur.execute("SELECT version();")
    db_version = cur.fetchone()
    print("PostgreSQL数据库版本:", db_version)

except psycopg2.OperationalError as e:
    print(f"数据库连接失败：{e}")
finally:
    # 关闭cursor和连接
    if 'cur' in locals():
        cur.close()
    if 'conn' in locals() and conn is not None:
        conn.close()