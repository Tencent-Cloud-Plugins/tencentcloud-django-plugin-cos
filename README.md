# Tencent Cloud Django COS Storage

腾讯云对象存储（COS）服务 for Django。

## 环境要求

Python: >=3.7, <4

Django: >=2.2, <3.3

## 安装

```
pip install tencentcloud-django-cos-storage
```

## 基本使用

在项目的 settings.py 中设置 `DEFAULT_FILE_STORAGE`：

```python
DEFAULT_FILE_STORAGE = "django_cos_storage.TencentCOSStorage"
```

此外，还需要设置腾讯云对象存储服务相关的必要信息：

```python
TENCENTCOS_STORAGE = {
    "BUCKET": "存储桶名称",
    "CONFIG": {
        "Region": "地域信息",
        "SecretId": "密钥 SecretId",
        "SecretKey": "密钥 SecretKey",
    }
}
```

详情可参考 [腾讯云对象存储官方文档](https://cloud.tencent.com/document/product/436)

## 设置

### 示例
```python
TENCENTCOS_STORAGE = {
    # 存储桶名称，必填
    "BUCKET": "存储桶名称",
    # 存储桶文件根路径，选填，默认 '/'
    "ROOT_PATH": "/",
    # 上传文件时最大缓冲区大小（单位 MB），选填，默认 100
    "UPLOAD_MAX_BUFFER_SIZE": 100,
    # 上传文件时分块大小（单位 MB），选填，默认 10
    "UPLOAD_PART_SIZE": 10,
    # 上传并发上传时最大线程数，选填，默认 5
    "UPLOAD_MAX_THREAD": 5,
    # 腾讯云存储 Python SDK 的配置参数，详细说明请参考腾讯云官方文档。
    # 注意：CONFIG中字段的大小写请与python-sdk中CosConfig的构造参数保持一致
    "CONFIG": {
        "Region": "地域信息",
        "SecretId": "密钥 SecretId",
        "SecretKey": "密钥 SecretKey",
    }
}
```

### 说明

**BUCKET**

> 存储桶名称，必填

**ROOT_PATH**
> 文件根路径，选填，默认为 '/'

**UPLOAD_MAX_BUFFER_SIZE**

> 上传文件时最大缓冲区大小（单位 MB），选填，默认 100。
> 其中缓冲区是一个线程安全队列，队列的元素为单个文件分块，队列中所有分块的大小加起来不超过 `UPLOAD_MAX_BUFFER_SIZE`。

**UPLOAD_PART_SIZE**
> 上传文件时分块大小（单位 MB），选填，默认 10。
> `UPLOAD_MAX_BUFFER_SIZE` 和 `UPLOAD_PART_SIZE` 共同决定了缓冲队列的大小，即 `QueueSize` = `UPLOAD_MAX_BUFFER_SIZE` / `UPLOAD_PART_SIZE`。

**UPLOAD_MAX_THREAD**

> 并发上传的最大线程数，选填，默认 5。
> 当文件的大小超过 `UPLOAD_PART_SIZE` 时将使用分块的方式并发上传文件，此配置项设置并发上传的最大线程数。如果文件大小不超过 `UPLOAD_PART_SIZE`，则不会使用分块的方式上传，此时该配置项不起任何作用。

**CONFIG**
> 注意：CONFIG中字段的大小写请与python-sdk中CosConfig的构造参数保持一致
> 
> 腾讯云对象存储 Python SDK 的配置参数，其中 `Region`、`SecretId`、`SecretKey` 为必填参数。
> 关于配置参数的详细说明请参考 [腾讯云对象存储 Python SDK 官方文档](https://cloud.tencent.com/document/product/436/12269)

