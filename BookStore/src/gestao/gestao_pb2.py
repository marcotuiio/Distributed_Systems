# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: gestao.proto
# Protobuf Python Version: 5.26.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0cgestao.proto\x12\x06gestao\":\n\rDadosConsulta\x12\x16\n\x0esession_cookie\x18\x01 \x01(\t\x12\x11\n\tid_pedido\x18\x02 \x01(\t\"\x19\n\x07IdLivro\x12\x0e\n\x06titulo\x18\x01 \x01(\t\"Y\n\x0cStatusPedido\x12\x1f\n\x06livros\x18\x01 \x03(\x0b\x32\x0f.gestao.IdLivro\x12\x13\n\x0bpreco_total\x18\x02 \x01(\x05\x12\x13\n\x0b\x64ono_pedido\x18\x03 \x01(\t\"#\n\tDadosUser\x12\x16\n\x0esession_cookie\x18\x01 \x01(\t\"/\n\x0cHistorioUser\x12\x1f\n\x06livros\x18\x01 \x03(\x0b\x32\x0f.gestao.IdLivro2\x8e\x01\n\rGestaoPedidos\x12>\n\x0f\x43onsultarPedido\x12\x15.gestao.DadosConsulta\x1a\x14.gestao.StatusPedido\x12=\n\x12\x43onsultarHistorico\x12\x11.gestao.DadosUser\x1a\x14.gestao.HistorioUserb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'gestao_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_DADOSCONSULTA']._serialized_start=24
  _globals['_DADOSCONSULTA']._serialized_end=82
  _globals['_IDLIVRO']._serialized_start=84
  _globals['_IDLIVRO']._serialized_end=109
  _globals['_STATUSPEDIDO']._serialized_start=111
  _globals['_STATUSPEDIDO']._serialized_end=200
  _globals['_DADOSUSER']._serialized_start=202
  _globals['_DADOSUSER']._serialized_end=237
  _globals['_HISTORIOUSER']._serialized_start=239
  _globals['_HISTORIOUSER']._serialized_end=286
  _globals['_GESTAOPEDIDOS']._serialized_start=289
  _globals['_GESTAOPEDIDOS']._serialized_end=431
# @@protoc_insertion_point(module_scope)
