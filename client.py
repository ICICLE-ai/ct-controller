import marimo

__generated_with = "0.16.3"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import requests
    import json
    import httpx
    from collections import deque
    import asyncio
    return asyncio, deque, httpx, json, mo, requests


@app.cell
def _(mo):
    mo.md(r"""# CTController Client""")
    return


@app.cell
def _(mo):
    user_controller_ip = mo.ui.text(value=f'http://127.0.0.1:8080', label='CTController IP: ', full_width=True)
    user_controller_ip
    return (user_controller_ip,)


@app.cell
def _(user_controller_ip):
    controller_ip = user_controller_ip.value
    return (controller_ip,)


@app.cell
def _(controller_ip, requests):
    def get_request(endpoint):
        try:
            response = requests.get(f"{controller_ip}/{endpoint}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return(f"Error fetching data from {endpoint}: {e}")
    return (get_request,)


@app.cell
def _(controller_ip, requests):
    def post_request(endpoint, payload={}):
        try:
            response = requests.post(f"{controller_ip}/{endpoint}", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return(f"Error posting data to {endpoint}: {e}")
    return (post_request,)


@app.cell
def _(controller_ip, requests):
    def file_get_request(endpoint):
        try:
            response = requests.get(f"{controller_ip}/{endpoint}")
            response.raise_for_status()
            return response.content.decode('utf-8')
        except requests.RequestException as e:
            return(f"Error fetching file from {endpoint}: {e}")
    return (file_get_request,)


@app.cell
def _(get_request):
    def check_health():
        return get_request('health')
    return


@app.cell
def _():
    default_config_payload = {
        "gpu": "false",
        "ckn_mqtt_broker": "10.169.143.160",
        "ct_version": "test",
        "mode": "demo",
        "model": "yolov5nu_ep120_bs32_lr0.001_0cfb1c03.pt",
        "inference_server": "false",
        "detection_thresholds": "{\"animal\": \"0.7\", \"image_store_save_threshold\": \"0\", \"image_store_reduce_save_threshold\": \"0\"}"
    }
    return (default_config_payload,)


@app.cell
def _(config_payload_box, json):
    config_payload = json.loads(config_payload_box.value)
    return (config_payload,)


@app.cell
def _(mo):
    startup_button = mo.ui.run_button(label='Startup', kind='success')
    configure_button = mo.ui.run_button(label='Configure', kind='warn')
    run_button = mo.ui.run_button(label='Run', kind='success')
    stop_button = mo.ui.run_button(label='Stop', kind='danger')
    shutdown_button = mo.ui.run_button(label='Shutdown', kind='danger')
    health_button = mo.ui.run_button(label='Check Health')
    dl_logs_button = mo.ui.run_button(label='Controller Logs')
    dl_config_button = mo.ui.run_button(label='Config')
    dl_app_out_button = mo.ui.run_button(label='App Stdout')
    dl_app_err_button = mo.ui.run_button(label='App Stderr')
    stream_app_button = mo.ui.switch(label='Stream App Logs')
    show_hide_stream_button = mo.ui.switch(label='Show Camera Stream')
    return (
        configure_button,
        dl_app_err_button,
        dl_app_out_button,
        dl_config_button,
        dl_logs_button,
        health_button,
        run_button,
        show_hide_stream_button,
        shutdown_button,
        startup_button,
        stop_button,
        stream_app_button,
    )


@app.cell
def _(
    configure_button,
    dl_app_err_button,
    dl_app_out_button,
    dl_config_button,
    dl_logs_button,
    health_button,
    mo,
    run_button,
    shutdown_button,
    startup_button,
    stop_button,
):
    mo.vstack(
        [
            mo.hstack([startup_button, configure_button, run_button, stop_button, shutdown_button], justify='center', gap=1.5),
            mo.hstack([health_button, dl_logs_button, dl_config_button, dl_app_out_button, dl_app_err_button], justify='center', gap=1.5),
        ],           
        gap=2
    )
    return


@app.cell
def _(default_config_payload, json, mo):
    config_payload_box = mo.ui.text_area(value=json.dumps(default_config_payload, indent=2), label='Configuration: ', full_width=True, rows=10)
    config_payload_box
    return (config_payload_box,)


@app.cell
def _():
    #stream_task = None
    state = {'stream_task': None, 'show_stream': False, 'stream_frame': None}
    return (state,)


@app.cell
def _(
    config_payload,
    configure_button,
    dl_app_err_button,
    dl_app_out_button,
    dl_config_button,
    dl_logs_button,
    file_get_request,
    get_request,
    health_button,
    json,
    post_request,
    run_button,
    shutdown_button,
    startup_button,
    state,
    stop_button,
):
    mapping = [
        (startup_button, (lambda: post_request('startup'), False)),
        (configure_button, (lambda: post_request('configure', config_payload), False)),
        (run_button, (lambda: post_request('run'), False)),
        (stop_button, (lambda: post_request('stop'), False)),
        (shutdown_button, (lambda: post_request('shutdown'), False)),
        (dl_logs_button, (lambda: file_get_request('controller_logs/download'), False)),
        (dl_config_button, (lambda: file_get_request('dl_config'), False)),
        (health_button, (lambda: get_request('health'), False)),
        (dl_app_out_button, (lambda: file_get_request('app_logs/download/stdout'), False)),
        (dl_app_err_button, (lambda: file_get_request('app_logs/download/stderr'), False)),
        #(stream_app_button, (lambda: launch_stream(state, endpoint='app_logs/stream', response_output=response_output), True)),
    ]
    response_output = ''
    counter = 0

    for button, (fhandle, is_stream) in mapping:
        if button.value:
            if state["stream_task"] and not state["stream_task"].done():
                 state["stream_task"].cancel()
            if is_stream:
                state["stream_task"] = fhandle()
            else:
                result = fhandle()
                if isinstance(result, dict):
                    response_output = json.dumps(result, indent=2)
                elif result is None:
                    pass
                else:
                    response_output = str(result)
                state['response_output'] = response_output
            response_output = state['response_output']
            counter = (counter + 1) % 2
    return counter, response_output


@app.cell
def _(counter, state):
    header = counter
    if state.get('response_output'):
        header = state['response_output'].split('\n')[0]
    else:
        header = ''
    print(header)
    return


@app.cell
def _(mo, response_output):
    mo.ui.text_area(
            value=response_output,
            label="API Response",
            full_width=True,
            disabled=True,
            rows=10
        )
    return


@app.cell
def _(asyncio, deque, httpx):
    async def tail_stream(url, n=100):
        buffer = deque(maxlen=n)

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                async for chunk in response.aiter_text():
                    for line in chunk.splitlines():
                        buffer.append(line)
                    yield "\n".join(buffer)
                    await asyncio.sleep(0)
    return (tail_stream,)


@app.cell
def _(asyncio, controller_ip, tail_stream):
    def launch_stream(state, endpoint, response_output):
        if state.get('stream_task') is None or state.get('stream_task').done():
            async def stream_runner():
                async for text in tail_stream(f'{controller_ip}/{endpoint}', n=10):
                    state['response_output'] = text
            state['stream_task'] = asyncio.create_task(stream_runner())
            return state['stream_task']
            #stream_task = asyncio.create_task(tail_stream(f'{controller_ip}/{endpoint}', n=10))
    return


@app.cell
def _(mo, show_hide_stream_button):
    mo.hstack([show_hide_stream_button], justify='center')
    return


@app.cell
def _(mo, show_hide_stream_button, user_controller_ip):
    video_port = 8081
    host_ip = ':'.join(user_controller_ip.value.split(':')[:-1])
    video_ip = f'{host_ip}:{video_port}'

    if show_hide_stream_button.value:
        stream_frame = mo.Html(f'<div style="display: flex; justify-content: center"><img src={video_ip} /></div>')
    else:
        stream_frame = None
    stream_frame
    return


@app.cell
def _(mo, stream_app_button):
    mo.hstack([stream_app_button], justify='center')
    return


@app.cell
def _(controller_ip, mo, stream_app_button):
    if stream_app_button.value:
        app_stream = mo.iframe(f'{controller_ip}/app_logs/stream')
    else:
        app_stream = None
    app_stream
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
