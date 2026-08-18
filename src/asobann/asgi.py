import socketio
import uvicorn
import uvloop

import asobann
import asobann.app


async def _serve():
    # create_app()とuvicornのサーバは同じイベントループで動かす必要がある。
    # AsyncMongoClientは生成時のイベントループにバインドされるため、
    # uvloop.run()を2回に分けて呼ぶと「別のイベントループで使われた」エラーになる。
    quart_app = await asobann.app.create_app()
    app = socketio.ASGIApp(quart_app.sio, quart_app)

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=quart_app.config.get("PORT", 5000),
        access_log=quart_app.config["ACCESS_LOG"],
    )
    server = uvicorn.Server(config)
    try:
        await server.serve()
    finally:
        # AsyncMongoClientはトポロジ監視のバックグラウンドタスクを持つ。閉じずに
        # 落とすと、SIGTERM後もそれが残ったままプロセスが終わる。Fargateのタスク
        # 停止時に無意味なログが出る程度だが、graceful shutdownとしては宙ぶらりん。
        await quart_app.mongo_client.aclose()


if __name__ == '__main__':
    # asyncio.run()ではなくuvloop.run()で起動する。uvicorn.Server.serve()を
    # 自前のループの中でawaitしているため、uvicornが素通りする
    # uvicorn.Config.setup_event_loop()は通らない。uvicorn[standard]を依存に
    # 足すだけではuvloopは使われず、ここで明示的にループを差し替える必要がある。
    uvloop.run(_serve())
