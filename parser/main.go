package main

import (
	"context"
	"encoding/base64"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/chromedp/chromedp"
	"github.com/gin-gonic/gin"
)

// ссылки на все журналы
var journalLinks = map[string]string{
	"Python":     "https://college.snation.kz/kz/tko/control/journals/873776",
	"БД":         "https://college.snation.kz/kz/tko/control/journals/873763",
	"ИКТ":        "https://college.snation.kz/kz/tko/control/journals/873757",
	"Графика":    "https://college.snation.kz/kz/tko/control/journals/873751",
	"Физра":      "https://college.snation.kz/kz/tko/control/journals/873753",
	"Экономика":  "https://college.snation.kz/kz/tko/control/journals/873760",
}

func main() {
	r := gin.Default()

	r.POST("/parse", func(c *gin.Context) {
		var creds struct {
			Login    string `json:"login"`
			Password string `json:"password"`
		}
		if err := c.BindJSON(&creds); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "bad request"})
			return
		}

		screens, err := parseSmartNation(creds.Login, creds.Password)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error":   "parse error",
				"details": err.Error(),
			})
			return
		}

		c.JSON(http.StatusOK, gin.H{"screenshots": screens})
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	r.Run("0.0.0.0:" + port)
}

// основная логика парсинга
func parseSmartNation(login, pass string) (map[string]string, error) {
	ctx, cancel := chromedp.NewContext(context.Background())
	defer cancel()
	ctx, cancel = context.WithTimeout(ctx, 180*time.Second)
	defer cancel()

	screens := make(map[string]string)

	fmt.Println("🚀 Логинимся в SmartNation...")

	// логинимся
	err := chromedp.Run(ctx,
		chromedp.Navigate(`https://college.snation.kz/kz/tko/login`),
		chromedp.WaitVisible(`input[aria-label="ЖСН"]`, chromedp.ByQuery),
		chromedp.Sleep(1*time.Second),

		// ввод логина и пароля
		chromedp.SendKeys(`input[aria-label="ЖСН"]`, login),
		chromedp.Sleep(500*time.Millisecond),
		chromedp.SendKeys(`input[aria-label="Құпия сөз"]`, pass),
		chromedp.Sleep(500*time.Millisecond),

		// нажать "Жүйеге кіру"
		chromedp.Click(`button[type="submit"]`, chromedp.ByQuery),
		chromedp.Sleep(7*time.Second),
	)
	if err != nil {
		return nil, fmt.Errorf("ошибка входа: %v", err)
	}

	fmt.Println("✅ Вход выполнен, начинаю обход журналов...")

	// проходим по каждому журналу
	for name, link := range journalLinks {
		fmt.Println("📘 Загружаю:", name)
		var buf []byte
		err := chromedp.Run(ctx,
			chromedp.Navigate(link),
			chromedp.Sleep(6*time.Second),
			chromedp.FullScreenshot(&buf, 90),
		)
		if err != nil {
			fmt.Println("❌ Ошибка при загрузке", name, ":", err)
			screens[name] = "error"
			continue
		}
		screens[name] = base64.StdEncoding.EncodeToString(buf)
		fmt.Println("✅ Скриншот сохранён:", name)
	}

	fmt.Println("🎉 Все журналы обработаны!")
	return screens, nil
}
