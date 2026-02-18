# test_load.py (新版本：结合自动加载和手动 Pooling fallback)
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoModel, AutoTokenizer
from sentence_transformers.models import Pooling, Normalize

# 指定模型路径（调整为您的本地路径；或用 'BAAI/bge-small-zh-v1.5' 自动下载/重载）
model_path = r'\baizeOS\models\embedding\bge-small-zh-v1.5'

try:
    # 步骤2: 首选自动加载 SentenceTransformer（会自动处理 Pooling）
    model = SentenceTransformer(model_path)
    print("模型自动加载成功！（使用 SentenceTransformer）")

except Exception as auto_error:
    print(f"自动加载失败: {auto_error}. 切换到手动加载模式...")

    try:
        # 步骤3: 手动加载 Bert + Pooling + Normalize（fallback）
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        bert_model = AutoModel.from_pretrained(model_path)

        # 从 config 获取 hidden_size，作为 word_embedding_dimension
        hidden_size = bert_model.config.hidden_size  # 对于 bge-small-zh-v1.5 是 384
        pooling_layer = Pooling(word_embedding_dimension=hidden_size, pooling_mode='mean')  # 指定 pooling_mode，如果默认是 mean pooling
        normalize_layer = Normalize()  # bge 模型通常需要 normalization

        # 组合成 SentenceTransformer 模型
        modules = [bert_model, pooling_layer, normalize_layer]
        model = SentenceTransformer(modules=modules)
        print("模型手动加载成功！（使用自定义 Pooling）")

    except Exception as manual_error:
        print(f"手动加载失败: {manual_error}")
        raise

# 测试 embedding（无论哪种加载方式）
sentences = ["这是一个测试句子。", "另一个中文句子。"]
embeddings = model.encode(sentences, normalize_embeddings=True)
print("Embeddings shape:", embeddings.shape)  # 预期: (2, 384)

# 测试相似度（可选）
from sentence_transformers.util import cos_sim
similarity = cos_sim(embeddings[0], embeddings[1])
print("句子相似度:", similarity)