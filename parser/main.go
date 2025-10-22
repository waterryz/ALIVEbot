package main

import (
	"context"
	"encoding/base64"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/chromedp/chromedp"
	"github.com/gin-gonic/gin"
)

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

		imageBase64, err := parseSmartNation(creds.Login, creds.Password)
		if err != nil {
			fmt.Println("❌ Ошибка парсинга:", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "parse error"})
			return
		}

		c.JSON(http.StatusOK, gin.H{"screenshot": imageBase64})
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	r.Run(":" + port)
}

func parseSmartNation(login, pass string) (string, error) {
	ctx, cancel := chromedp.NewContext(context.Background())
	defer cancel()

	ctx, cancel = context.WithTimeout(ctx, 60*time.Second)
	defer cancel()

	var buf []byte
	err := chromedp.Run(ctx,
		chromedp.Navigate(`https://college.snation.kz/kz/tko/login`),
		chromedp.Sleep(3*time.Second),
		chromedp.SendKeys(`#login-email`, login),
		chromedp.Sleep(1*time.Second),
		chromedp.SendKeys(`#login-password`, pass),
		chromedp.Sleep(1*time.Second),
		chromedp.Click(`button[type="submit"]`),
		chromedp.Sleep(8*time.Second),
		chromedp.FullScreenshot(&buf, 90),
	)
	if err != nil {
		return "", err
	}

	return base64.StdEncoding.EncodeToString(buf), nil
}
