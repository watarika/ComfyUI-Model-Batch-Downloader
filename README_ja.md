# ComfyUI Model Batch Downloader

[<a href="README.md">English</a>] [日本語]

Hugging Face、Civitai、任意のHTTP/HTTPS URLから複数のComfyUIモデルファイルを`aria2c`で取得し、対応するファイルを同じComfyUIキュー内でロードするカスタムノードです。保存先は13カテゴリで、`checkpoints`、`diffusion_models`、`text_encoders`、`vae`、`loras`、`controlnet`、`embeddings`、`upscale_models`、`onnx`、`sam3`、`llm`、`ultralytics_bbox`、`ultralytics_segm`に対応しています。

既存ファイルは上書きせず、チェックサム検証も行いません。`.aria2`サイドカーがある未完了ファイルは継続ダウンロードします。

## 必要なもの

- ComfyUI
- Python 3.10以上
- `aria2c`コマンド（ComfyUIを起動する環境の`PATH`から実行できること）

`aria2c`はこのリポジトリには同梱せず、自動インストールもしません。

## インストール

ComfyUIのディレクトリで実行します。

```powershell
git clone https://github.com/watarika/ComfyUI-Model-Batch-Downloader.git custom_nodes/ComfyUI-Model-Batch-Downloader
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

CivitaiのダウンロードURLには`civitai.red`を推奨します。`https://civitai.red/api/download/models/{modelVersionId}`を使用してください。`civitai.com`のダウンロードURLは非推奨で、特に制限付きファイルやNSFWファイルではHTTP 403になる可能性があります。

## ノード

- `Model Download Batch`: 追加・削除ボタンのある一覧UI。内部ではcanonical JSONを保持します。
- `Model Download Batch (JSON)`: 同じコアを使うJSON直接入力版です。
- `Load Checkpoint (Downloaded)`: `checkpoints`カテゴリのモデルをComfyUI標準のcheckpoint loaderと同じ動作でロードします。
- `Load Diffusion Model (Downloaded)`: `diffusion_models`カテゴリのモデルをComfyUI標準のdiffusion model loaderと同じ動作でロードします。
- `Load CLIP (Downloaded)`: ComfyUI標準の`Load CLIP`と同じ`type`の選択肢を使用します。`krea2`、`ideogram4`、`flux2`などを選択できます。
- `Load VAE (Downloaded)`: `vae`カテゴリのモデルをComfyUI標準のVAE loaderと同じ動作でロードします。
- `Load ControlNet (Downloaded)`: `controlnet`カテゴリのモデルをComfyUI標準のControlNet loaderと同じ動作でロードします。
- `Load Upscale Model (Downloaded)`: `upscale_models`カテゴリのモデルをComfyUI標準のupscale model loaderと同じ動作でロードします。
- `Load LoRA (Downloaded)`: `loras`カテゴリのモデルをComfyUI標準のLoRA loaderと同じ動作でロードします。model-only LoRAでは`strength_clip`を0にできます。

2種類のdownload nodeは、任意型の`passthrough`を入力と出力に持ちます。既存の接続途中に挿入できるほか、未接続でもoutput nodeとして実行できます。取得結果を使う場合は`download_result`を対応するDownloaded Loaderへ接続し、manifestの`id`を指定します。

## 利用例

次のmodel familyは一般的な構成を示す例であり、互換性のあるモデルを網羅する一覧ではありません。

- Illustrious: 一体型checkpointを`checkpoints`へダウンロードし、`Load Checkpoint (Downloaded)`でロードします。
- Anima: 個別のdiffusion model、text encoder、VAEをそれぞれ`diffusion_models`、`text_encoders`、`vae`へダウンロードし、対応するDownloaded Loaderでロードします。
- Krea 2: 個別のdiffusion modelとVAEを`diffusion_models`と`vae`へダウンロードします。text encoderは`text_encoders`へダウンロードし、`Load CLIP (Downloaded)`で`krea2`を選択します。

## ダウンロード進捗

実行中のdownload nodeには、KSamplerと同じComfyUI標準の進捗バーが表示されます。複数ファイルの場合もバーはリセットせず、バッチ全体を0～100%として進みます。

ComfyUIのログには約1秒ごとに現在のID、進捗率、速度、ETAを表示します。

```text
[Model Batch Downloader] anima_model 42%  18.3MiB  ETA 31s
```

認証トークンと認証済みURLはログへ出力しません。

## Manifest

ルートは1件以上のJSON配列です。各項目で使えるフィールドは次のとおりです。

| フィールド | 必須 | 内容 |
|---|---:|---|
| `url` | はい | HTTP/HTTPS URL |
| `model_type` | はい | 下の互換性表にある13カテゴリのいずれか |
| `subfolder` | いいえ | 対応するComfyUI model root配下の保存先 |
| `filename` | いいえ | 省略時はレスポンスまたはURLから解決 |
| `id` | いいえ | 省略時はfilenameの最後の拡張子を除いた値 |
| `split` | いいえ | 1～16、既定値16 |

`subfolder`を指定しない場合、各カテゴリは次のディレクトリを使用します。そのカテゴリにComfyUIのfolder pathが設定されている場合は、次の既定値より設定が優先されます。

| `model_type` | 既定のディレクトリ | 対応loader / consumer |
|---|---|---|
| `checkpoints` | `models/checkpoints` | `Load Checkpoint (Downloaded)` |
| `diffusion_models` | `models/diffusion_models` | `Load Diffusion Model (Downloaded)` |
| `text_encoders` | `models/text_encoders` | `Load CLIP (Downloaded)` |
| `vae` | `models/vae` | `Load VAE (Downloaded)` |
| `loras` | `models/loras` | `Load LoRA (Downloaded)` |
| `controlnet` | `models/controlnet` | `Load ControlNet (Downloaded)` |
| `embeddings` | `models/embeddings` | ComfyUIのプロンプト参照。companion loaderなし |
| `upscale_models` | `models/upscale_models` | `Load Upscale Model (Downloaded)` |
| `onnx` | `models/onnx` | Impact Pack |
| `sam3` | `models/sam3` | `comfyui-sam3`のpath-based `(down)Load SAM3 Model`。既定値`models/sam3/sam3.pt` |
| `llm` | `models/llm` | `ComfyUI_LLM_SDXL_Adapter`: `LLM Model Loader` / `LLM GGUF Model Loader`。companion loaderなし |
| `ultralytics_bbox` | `models/ultralytics/bbox` | Impact Subpack |
| `ultralytics_segm` | `models/ultralytics/segm` | Impact Subpack |

embeddingファイルはプロンプト参照で使用し、companion loaderはありません。`comfyui-sam3`はpath-based `(down)Load SAM3 Model`へpath文字列を渡して使用します。その既定値`models/sam3/sam3.pt`はこのdownloaderのSAM3既定保存先を指しますが、このdownloaderはSAM3 companion loaderを提供しません。LLMファイルは`ComfyUI_LLM_SDXL_Adapter`の`LLM Model Loader`または`LLM GGUF Model Loader`で`models/llm`から読み込みます。LLM対応は単一ファイルのダウンロードのみで、リポジトリsnapshotや複数ファイル推論を自動提供しません。Impact Pack、`comfyui-sam3`、`ComfyUI_LLM_SDXL_Adapter`、Impact Subpackなどの任意のcustom nodeはこのdownloaderの依存関係ではありません。consumer nodeが必要な場合は別途インストールして使用してください。

推奨ドメインを使うCivitai LoRAの例:

```json
[
  {
    "url": "https://civitai.red/api/download/models/{modelVersionId}",
    "model_type": "loras",
    "id": "civitai_lora",
    "filename": "civitai_lora.safetensors"
  }
]
```

Animaの具体的な利用例:

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
- Civitaiで401/403: 推奨する`civitai.red`のダウンロードURLを使用し、`CIVITAI_API_TOKEN`を確認してください。トークンが有効でも`civitai.com`のURLは失敗する場合があります。
- `duplicate id`: どちらかに一意の`id`を明示してください。
- category mismatch: IDの`model_type`に対応するDownloaded Loaderへ接続してください。
- 拡張カテゴリのloaderがない: 互換性表に記載したconsumerを使用してください。外部consumer pluginのインストールと保守は各plugin側が担い、このdownloaderは選択した保存先へのファイル取得だけを担います。
