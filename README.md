# ComfyUI Model Batch Downloader

Hugging Face、Civitai、通常のHTTP URLから複数のモデルファイルを`aria2c`で取得し、同じComfyUIキュー内でロードするカスタムノードです。Illustrious、Anima、Krea 2で使うチェックポイント、diffusion model、text encoder、VAE、LoRAを対象にしています。

既存ファイルは上書きせず、チェックサム検証も行いません。`.aria2`サイドカーがある未完了ファイルは継続ダウンロードします。

## 必要なもの

- ComfyUI
- Python 3.10以上
- `aria2c`コマンド（ComfyUIを起動する環境の`PATH`から実行できること）

`aria2c`はこのリポジトリには同梱せず、自動インストールもしません。

## インストール

ComfyUIのディレクトリで実行します。

```powershell
git clone <repository-url> custom_nodes/ComfyUI-Model-Batch-Downloader
```

その後、ComfyUIを再起動してください。追加のPythonパッケージはありません。

## 認証

トークンはノードやワークフローJSONに入力せず、ComfyUIを起動するプロセスの環境変数に設定します。

| サービス | 環境変数 |
|---|---|
| Hugging Face | `HF_TOKEN` |
| Civitai | `CIVITAI_API_TOKEN` |

PowerShellの例:

```powershell
$env:HF_TOKEN = "hf_..."
$env:CIVITAI_API_TOKEN = "..."
python main.py
```

Linuxの例:

```bash
export HF_TOKEN='hf_...'
export CIVITAI_API_TOKEN='...'
python main.py
```

トークンは対応ドメインにだけ付与され、manifest、`DOWNLOAD_RESULT`、画面の状態には保存されません。

## ノード

- `Model Download Batch`: 追加・削除ボタンのある一覧UI。内部ではcanonical JSONを保持します。
- `Model Download Batch (JSON)`: 同じコアを使うJSON直接入力版です。
- `Downloaded Checkpoint Loader`: Illustriousなどの一体型checkpointをロードします。
- `Downloaded Diffusion Model Loader`: AnimaやKrea 2のdiffusion modelをロードします。
- `Downloaded Text Encoder Loader`: Animaでは`auto`、Krea 2では`krea2`を選びます。
- `Downloaded VAE Loader`: Qwen Image VAEなどをロードします。
- `Downloaded LoRA Loader`: 対応LoRAをロードします。model-only LoRAでは`strength_clip`を0にできます。

2種類のdownload nodeは、任意型の`passthrough`を入力と出力に持ちます。既存の接続途中に挿入できるほか、未接続でもoutput nodeとして実行できます。取得結果を使う場合は`download_result`を対応するDownloaded Loaderへ接続し、manifestの`id`を指定します。

## Manifest

ルートは1件以上のJSON配列です。各項目で使えるフィールドは次のとおりです。

| フィールド | 必須 | 内容 |
|---|---:|---|
| `url` | はい | HTTP/HTTPS URL |
| `model_type` | はい | `checkpoints`, `diffusion_models`, `text_encoders`, `vae`, `loras` |
| `subfolder` | いいえ | 対応するComfyUI model root配下の保存先 |
| `filename` | いいえ | 省略時はレスポンスまたはURLから解決 |
| `id` | いいえ | 省略時はfilenameの最後の拡張子を除いた値 |
| `split` | いいえ | 1～16、既定値16 |

Anima向けの例:

```json
[
  {
    "url": "https://huggingface.co/owner/repo/resolve/main/anima-model.safetensors",
    "model_type": "diffusion_models",
    "subfolder": "anima",
    "id": "anima_model",
    "split": 16
  },
  {
    "url": "https://huggingface.co/owner/repo/resolve/main/qwen3-0.6b.safetensors",
    "model_type": "text_encoders",
    "subfolder": "anima",
    "id": "anima_encoder"
  },
  {
    "url": "https://huggingface.co/owner/repo/resolve/main/qwen-image-vae.safetensors",
    "model_type": "vae",
    "id": "qwen_vae"
  }
]
```

`download_result`を3つの対応loaderへ接続し、それぞれ`anima_model`、`anima_encoder`、`qwen_vae`を指定します。

URLが`model.fp16.safetensors`へ解決され、`id`が省略されていればIDは`model.fp16`です。URL末尾からfilenameを判断できないCivitai APIなどでは、一覧UIの`Resolve filename / ID`で事前解決できます。JSON版で安定して参照したい場合は明示的な`id`を推奨します。

## 既存ファイルとエラー

- 完成済みファイルがあれば、aria2を起動せず`skipped`にします。
- `<filename>.aria2`があればaria2の継続モードで再開します。
- 複数項目は順番に処理し、1件が失敗しても残りを試します。最後に失敗をまとめて報告します。
- 保存先はComfyUIが設定している各model rootの配下だけに制限されます。
- 同じIDや同じ保存先がmanifest内で重複するとエラーになります。

## トラブルシューティング

- `aria2c is required`: `aria2c --version`がComfyUIと同じ環境で通るか確認し、ComfyUIを再起動してください。
- Hugging Faceで401/403: `HF_TOKEN`とリポジトリへのアクセス権を確認してください。
- Civitaiで401/403: `CIVITAI_API_TOKEN`を確認してください。
- `duplicate id`: どちらかに一意の`id`を明示してください。
- category mismatch: IDの`model_type`に対応するDownloaded Loaderへ接続してください。

## 開発時の確認

```powershell
uv run --with pytest --with aiohttp --no-project pytest tests -v
node --test tests-js/manifest_state.test.mjs
uvx ruff check .
```
