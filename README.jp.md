## ComfyUI-SaveImageWithMetaDataUniversal（日本語）
![SaveImageWithMetaData Preview](img/save_image_with_metadata_universal.png)

このパックは、ComfyUI 用の拡張「Save Image w/ Metadata Universal」ノードと補助ノード群を提供し、PNG / WebP / JPEG に拡張メタデータ（プロンプト、モデル/LoRA/埋め込み、サンプラー、ガイダンス、ワークフローなど）を保存します。JPEG は EXIF の上限 (~64KB) があるため段階的フォールバックを実装しています。

### インストール
```
cd <ComfyUIディレクトリ>/custom_nodes
git clone https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal.git
```

### 追加ノード
| ノード | 概要 |
| ---- | ---- |
| Save Image w/ Metadata Universal | 画像を保存し、PNGInfo / EXIF / WebP にメタデータを埋め込みます。 |
| Create Extra MetaData | 任意のキー/値メタデータを追加します。 |
| Metadata Rule Scanner | インストール済みノードをスキャンしてメタデータ取得ルールを提案します。 |
| Save Custom Metadata Rules | 生成したルールをユーザルールファイルへ保存します。 |
| Metadata Force Include | 強制対象ノードクラスを管理します。 |
| Show generated_user_rules.py | 現在のマージ済みユーザルールを表示します。 |
| Save generated_user_rules.py | 編集済みルールを検証して保存します。 |
| Show Text (UniMeta) | テキスト出力を表示（ローカルバリアント）。 |
| Show Any (Any to String) | 任意の入力を文字列化して表示し、`Create Extra MetaData` に接続可能な STRING を出力します。 |

### クイックスタート
1. `Metadata Rule Scanner` と `Save Custom Metadata Rules` を使ってルールを生成・保存します。
2. `Save Image w/ Metadata Universal` ノードを追加し、画像入力に接続して保存します。
3. 必要に応じて `Create Extra MetaData` で手動メタデータを追加します。
4. Civitai 互換の表記に近づける場合は `civitai_sampler` と `guidance_as_cfg` を有効化します。
5. フルのワークフロー埋め込みが必要な場合は PNG（または可逆 WebP）を推奨します（JPEG はサイズ制限あり）。

### サンプラー選択方法（Sampler Selection Method）
- KSampler ノードの選択方法を指定します。
- Farthest（最も遠い）/ Nearest（最も近い）/ By node ID（ID指定）から選択できます。

### 付与される主なメタデータ
- Positive/Negative prompt、Steps、Sampler、Scheduler、CFG、Guidance、Denoise、Shift 系
- Seed、Clip skip、Clip model、Size
- Model / VAE 名とハッシュ、LoRA 一覧（強度含む）、Embeddings（名前とハッシュ）
- バッチ情報（Batch index/size）
- ハッシュ一覧（Model / LoRA / Embeddings）

### JPEG のメタデータサイズとフォールバック
JPEG の EXIF は ~64KB 上限です。上限超過時は段階的に情報を削減します：
1) full → 2) reduced-exif → 3) minimal → 4) com-marker。発生時は `Metadata Fallback: <stage>` を末尾に付与します。

### 環境変数フラグ（抜粋）
| フラグ | 効果 |
| ---- | ---- |
| METADATA_NO_HASH_DETAIL | ハッシュ詳細 JSON を抑制 |
| METADATA_NO_LORA_SUMMARY | LoRA の集約行を抑制（UI の設定が優先） |
| METADATA_TEST_MODE | パラメータ文字列をテスト用の複数行モードに切替 |
| METADATA_DEBUG_PROMPTS | プロンプト取得のデバッグログを有効化 |

より詳しい情報は英語版 README と `docs/JPEG_METADATA_FALLBACK.md` を参照してください。
