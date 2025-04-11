import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

# ATENÇÃO: SEU TOKEN VAI AQUI (modo simples, direto na string)
TELEGRAM_TOKEN = "7953008015:AAH4JxQ0LY31kqoi77cpF3H1hfdIyJh6SAk"

# Estados da conversa
PRESCRICAO, EXECUCAO, TIPO_EXERCICIO, ANALISE = range(4)

# Inicializa o logger
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Variáveis temporárias
dados_usuario = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Vamos começar! Me diga a quantidade de séries e a faixa de repetições prescrita para o exercício.\n\n👉 Exemplo: 3x10-12")
    return PRESCRICAO

async def receber_prescricao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dados_usuario[update.effective_user.id] = {"prescricao": update.message.text}
    await update.message.reply_text("Agora me diga quantas repetições você fez em cada série e qual foi a carga usada.\n\n👉 Exemplo: 10,10,8 - 30kg")
    return EXECUCAO

async def receber_execucao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dados_usuario[update.effective_user.id]["execucao"] = update.message.text
    teclado = [["1", "2"], ["3", "4"]]
    await update.message.reply_text(
        "Pra te dar uma sugestão precisa, me diga o tipo de exercício que você está analisando:\n\n"
        "1️⃣ Isolado em máquina\n"
        "2️⃣ Isolado com peso livre\n"
        "3️⃣ Multiarticular em máquina\n"
        "4️⃣ Multiarticular com peso livre",
        reply_markup=ReplyKeyboardMarkup(teclado, one_time_keyboard=True)
    )
    return TIPO_EXERCICIO

async def receber_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dados_usuario[update.effective_user.id]["tipo"] = update.message.text
    resposta = analisar_dados(dados_usuario[update.effective_user.id])
    await update.message.reply_text(resposta)
    await update.message.reply_text("Deseja analisar outro exercício? Envie /start para recomeçar.")
    return ConversationHandler.END

def analisar_dados(dados):
    try:
        prescricao = dados["prescricao"]
        execucao = dados["execucao"]
        tipo = int(dados["tipo"])
        series_info, carga_info = execucao.split("-")
        reps = [int(x.strip()) for x in series_info.strip().split(",")]
        carga = float(carga_info.strip().lower().replace("kg", ""))
        series, faixa = prescricao.lower().split("x")
        faixa_min, faixa_max = [int(x) for x in faixa.split("-")]

        if any(r == 6 for r in reps):
            return (
                "⚠️ Uma ou mais séries tiveram apenas 6 repetições.\n"
                "Esse volume está ficando muito baixo para a hipertrofia ideal.\n\n"
                "📌 Recomendações para o próximo treino:\n"
                "❌ Não aumente a carga.\n"
                "✅ Mantenha a carga atual.\n"
                "🔄 Tente fazer pelo menos 8 repetições nas séries com 6 reps."
            )

        if all(r == faixa_min for r in reps):
            return (
                f"Você está no limite inferior da prescrição ({faixa_min} reps em todas as séries).\n"
                f"👉 Mantenha a carga atual.\n"
                f"👉 No próximo treino, tente fazer 1 a 2 repetições a mais em cada série."
            )

        if all(r == faixa_max for r in reps):
            novo_min = faixa_min - 2
            sugestao_carga = {
                1: (carga * 1.05, carga * 1.10),
                2: (carga * 1.04, carga * 1.08),
                3: (carga * 1.03, carga * 1.06),
                4: (carga * 1.025, carga * 1.05)
            }
            min_carga, max_carga = sugestao_carga[tipo]
            return (
                "✅ Excelente! Você atingiu o máximo da faixa em todas as séries.\n"
                f"📊 Nova faixa de repetições: {novo_min}-{faixa_max}\n"
                f"🔩 Aumente a carga para algo entre {round(min_carga)}kg e {round(max_carga)}kg."
            )

        if faixa_min <= min(reps) and max(reps) <= faixa_max:
            return (
                "📈 Você está evoluindo dentro da faixa.\n"
                "👉 Mantenha a carga atual.\n"
                "👉 Tente progredir até alcançar o topo da faixa de reps nas próximas sessões."
            )

        if len(set(reps)) >= 2:
            ultima = reps[-1]
            if ultima == faixa_min:
                return "📌 A última série foi o mínimo. Mantenha a carga e tente aumentar só essa série."
            elif ultima < faixa_max:
                return "📌 A última série foi intermediária. Mantenha a carga e tente aumentar todas as séries aos poucos."
            else:
                return "📌 A última série foi o máximo. Mantenha a carga e priorize equilibrar as séries anteriores."

        return "❗️Não consegui identificar um padrão claro. Por favor, revise os dados inseridos."

    except Exception as e:
        return f"❌ Erro ao processar os dados. Verifique o formato das informações. Erro: {str(e)}"

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Análise cancelada. Envie /start para começar de novo.")
    return ConversationHandler.END

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PRESCRICAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_prescricao)],
            EXECUCAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_execucao)],
            TIPO_EXERCICIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_tipo)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(conv_handler)
    app.run_polling()
